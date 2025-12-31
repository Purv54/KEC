from django.shortcuts import render,get_object_or_404,redirect
from django.contrib import messages
from django.urls import reverse
from .models import Category, Product, Order, OrderItem,Address,Wishlist
from django.db.models import Q
from django.views.decorators.http import require_POST
from .forms import CheckoutForm,AddressForm,SignUpForm,ProfileForm

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
import logging
logger = logging.getLogger(__name__)

from django.http import JsonResponse

import razorpay
from django.conf import settings

from rest_framework.decorators import api_view
from rest_framework.response import Response


from razorpay.errors import SignatureVerificationError
from store.utils import send_order_receipt

from django.core.mail import send_mail
from .models import PasswordResetOTP
from .utils import generate_otp
from django.contrib.auth.models import User

from django.contrib.auth.hashers import make_password

def home(request):
    categories = Category.objects.all()
    return render(request, 'store/home.html', 
                 {'categories': categories,})


def shop(request):
    categories = Category.objects.all()
    products = Product.objects.filter(is_available=True)
    
    # Category filter (?category=slug)
    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)
    
    # Search filter (?q=...)
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(model_number__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Get wishlist product IDs for current user
    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist_product_ids = list(
            Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
        )
    
    context = {
        'categories': categories,
        'products': products,
        'selected_category': category_slug,
        'search_query': query,
        'wishlist_product_ids': wishlist_product_ids,
    }
    return render(request, 'store/shop.html', context)

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_available=True)
    
    # Check if product is in wishlist
    is_in_wishlist = False
    if request.user.is_authenticated:
        is_in_wishlist = Wishlist.objects.filter(
            user=request.user, 
            product=product
        ).exists()
    
    return render(request, 'store/product_detail.html', {
        'product': product,
        'is_in_wishlist': is_in_wishlist,
    })

# ---------- CART HELPERS ----------

def _get_cart(request):
    """Return cart dict from session: {product_id: quantity}"""
    return request.session.get('cart', {})


def _save_cart(request, cart):
    """Save cart dict back to session"""
    request.session['cart'] = cart
    request.session.modified = True


# ---------- CART VIEWS ----------
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_available=True)

    cart = _get_cart(request)
    quantity = int(request.POST.get('quantity', 1))
    if quantity < 1:
        quantity = 1

    pid = str(product_id)
    current_qty = cart.get(pid, 0)
    new_qty = current_qty + quantity

    # Optional: respect stock
    if product.stock and new_qty > product.stock:
        new_qty = product.stock

    cart[pid] = new_qty
    _save_cart(request, cart)

    messages.success(request, f"Added {product.name} (x{quantity}) to cart.")

    # redirect back to previous page if 'next' is given
    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('store:cart_detail')

@login_required
def cart_detail(request):
    cart = _get_cart(request)
    items = []
    total = 0

    for pid, qty in cart.items():
        product = get_object_or_404(Product, id=pid)
        subtotal = product.price * qty
        total += subtotal
        items.append({
            'product': product,
            'quantity': qty,
            'subtotal': subtotal,
        })

    return render(request, 'store/cart.html', {
        'items': items,
        'total': total,
    })


@require_POST
def remove_from_cart(request, product_id):
    cart = _get_cart(request)
    pid = str(product_id)
    if pid in cart:
        del cart[pid]
        _save_cart(request, cart)
        messages.info(request, "Item removed from cart.")
    return redirect('store:cart_detail')


@require_POST
def clear_cart(request):
    request.session['cart'] = {}
    request.session.modified = True
    messages.info(request, "Cart cleared.")
    return redirect('store:cart_detail')

@require_POST
def update_cart(request, product_id):
    cart = _get_cart(request)
    pid = str(product_id)

    if pid not in cart:
        return redirect('store:cart_detail')

    product = get_object_or_404(Product, id=product_id)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        quantity = 1

    if quantity < 1:
        # if user sets 0 or less, remove the item
        del cart[pid]
        messages.info(request, f"{product.name} removed from cart.")
    else:
        # optional: cap by stock
        if product.stock and quantity > product.stock:
            quantity = product.stock
            messages.warning(request, f"Quantity adjusted to available stock ({product.stock}).")

        cart[pid] = quantity
        messages.success(request, f"Updated {product.name} quantity to {quantity}.")

    _save_cart(request, cart)
    return redirect('store:cart_detail')

@login_required
def checkout(request):
    cart = _get_cart(request)
    if not cart:
        messages.error(request, "Your cart is empty. Add some products before checkout.")
        return redirect('store:shop')

    # Build items + total for summary
    items = []
    total = 0
    for pid, qty in cart.items():
        product = get_object_or_404(Product, id=pid)
        subtotal = product.price * qty
        total += subtotal
        items.append({
            'product': product,
            'quantity': qty,
            'subtotal': subtotal,
        })

    # Load user's saved addresses if authenticated
    user_addresses = None
    if request.user.is_authenticated:
        user_addresses = request.user.addresses.all()

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'cod')
        # first check if a saved address id was posted
        logger.debug("Checkout POST data: %s", request.POST.dict())
        address_id = request.POST.get('address_id')
        form = CheckoutForm(request.POST)

        # If user selected a saved address and it's valid, we'll use it
        selected_address = None
        if address_id and request.user.is_authenticated:
            try:
                selected_address = Address.objects.get(id=address_id, user=request.user)
            except Address.DoesNotExist:
                selected_address = None

        if selected_address:
            if payment_method == 'online':
                request.session['checkout_data'] = {
                    'full_name': selected_address.full_name,
                    'email': request.user.email if request.user.is_authenticated else '',
                    'phone': selected_address.phone,
                    'address': selected_address.address_line,
                    'city': selected_address.city,
                    'pincode': selected_address.pincode,
                    'notes': '',
                }
                request.session['cart_snapshot'] = cart
                return redirect('store:razorpay_payment')
            
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    full_name=selected_address.full_name,
                    email=request.user.email if request.user.is_authenticated and request.user.email else '',
                    phone=selected_address.phone,
                    address=selected_address.address_line,
                    city=selected_address.city,
                    pincode=selected_address.pincode,
                    notes=''
                )

                # create order items
                for item in items:
                    OrderItem.objects.create(
                        order=order,
                        product=item['product'],
                        quantity=item['quantity'],
                        price=item['product'].price
                    )
                    # reduce stock
                    p = item['product']
                    if p.stock is not None:
                        p.stock = max(0, p.stock - item['quantity'])
                        p.save()

                # clear cart
                request.session['cart'] = {}
                request.session.modified = True

                messages.success(request, f"Your order #{order.id} has been placed successfully!")
                return redirect('store:order_success', order_id=order.id)

        else:
            # No saved address used — validate normal checkout form
            if form.is_valid():
                if payment_method == 'online':
                    request.session['checkout_data'] = request.POST.dict()
                    request.session['cart_snapshot'] = cart
                    return redirect('store:razorpay_payment')
                
                with transaction.atomic():
                    order = form.save(commit=False)
                    if request.user.is_authenticated:
                        order.user = request.user
                        # if email empty in form but user has email, you might want to set it
                        if not order.email and request.user.email:
                            order.email = request.user.email
                    order.save()

                    for item in items:
                        OrderItem.objects.create(
                            order=order,
                            product=item['product'],
                            quantity=item['quantity'],
                            price=item['product'].price
                        )
                        # reduce stock
                        p = item['product']
                        if p.stock is not None:
                            p.stock = max(0, p.stock - item['quantity'])
                            p.save()

                    # optionally: if user checked "save address" on form, create Address object here
                    # clear cart
                    request.session['cart'] = {}
                    request.session.modified = True

                    messages.success(request, f"Your order #{order.id} has been placed successfully!")
                    return redirect('store:order_success', order_id=order.id)
            else:
                messages.error(request, "Please correct errors in the form.")
    else:
        form = CheckoutForm()

    return render(request, 'store/checkout.html', {
        'form': form,
        'items': items,
        'total': total,
        'user_addresses': user_addresses,
    })

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/order_success.html', {'order': order})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('store:shop')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # optional: set email lowercased
            if user.email:
                user.email = user.email.lower()
                user.save()
            # Auto-login after signup
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account was created.")
            next_url = request.GET.get('next') or request.POST.get('next') or 'store:shop'
            return redirect(next_url)
    else:
        form = SignUpForm()
    return render(request, 'store/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('store:shop')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next') or request.GET.get('next') or None

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect(next_url or 'store:shop')
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('store:login')
    else:
        next_url = request.GET.get('next', '')
        return render(request, 'store/login.html', {'next': next_url})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('store:home')

@login_required
def profile_view(request):
    user = request.user
    # user info
    email = user.email
    # fetch addresses and orders
    addresses = user.addresses.all()
    orders = Order.objects.filter(user=user).order_by('-created_at')

    add_form = AddressForm()

    context = {
        'email': email,
        'addresses': addresses,
        'orders': orders,
        'add_form': add_form,
    }
    return render(request, 'store/profile.html', context)


@login_required
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            addr = form.save(commit=False)
            addr.user = request.user
            # if setting default, unset others
            if addr.is_default:
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
            addr.save()
            messages.success(request, "Address added.")
        else:
            # capture errors to show on the profile page
            for field, errs in form.errors.items():
                messages.error(request, f"{field}: {', '.join(errs)}")
    return redirect('store:profile')

@login_required
def edit_profile(request):
    user = request.user
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('store:profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProfileForm(instance=user)

    return render(request, 'store/edit_profile.html', {'form': form})


@login_required
def edit_address(request, address_id):
    # ensure the address belongs to this user
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            addr = form.save(commit=False)
            addr.user = request.user
            if addr.is_default:
                # unset other defaults
                Address.objects.filter(user=request.user, is_default=True).exclude(id=addr.id).update(is_default=False)
            addr.save()
            messages.success(request, "Address updated successfully.")
            return redirect('store:profile')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = AddressForm(instance=address)

    return render(request, 'store/edit_address.html', {'form': form, 'address': address})
    
@login_required
def set_default_address(request, address_id):
    """
    Mark the address with id=address_id as the user's default address.
    Only accepts POST for safety.
    """
    if request.method != "POST":
        return redirect('store:profile')

    addr = get_object_or_404(Address, id=address_id, user=request.user)

    # unset other defaults
    Address.objects.filter(user=request.user, is_default=True).exclude(id=addr.id).update(is_default=False)

    # set this one as default
    addr.is_default = True
    addr.save()

    messages.success(request, "Default address updated.")
    return redirect('store:profile')
    
@login_required
def wishlist_view(request):
    """Display user's wishlist"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    context = {
        'wishlist_items': wishlist_items
    }
    return render(request, 'store/wishlist.html', context)

@login_required
def add_to_wishlist(request, product_id):
    """Add product to wishlist"""
    product = get_object_or_404(Product, id=product_id)
    
    # Check if already in wishlist
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if created:
        messages.success(request, f'{product.name} added to wishlist!')
    else:
        messages.info(request, f'{product.name} is already in your wishlist.')
    
    # For AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': created,
            'message': 'Added to wishlist' if created else 'Already in wishlist'
        })
    
    return redirect(request.META.get('HTTP_REFERER', 'store:shop'))

@login_required
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist"""
    product = get_object_or_404(Product, id=product_id)
    
    try:
        wishlist_item = Wishlist.objects.get(user=request.user, product=product)
        wishlist_item.delete()
        messages.success(request, f'{product.name} removed from wishlist.')
        
        # For AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Removed from wishlist'})
            
    except Wishlist.DoesNotExist:
        messages.error(request, 'Item not found in wishlist.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Item not found'})
    
    return redirect(request.META.get('HTTP_REFERER', 'store:wishlist'))

@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    try:
        wishlist_item = Wishlist.objects.get(user=request.user, product=product)
        wishlist_item.delete()
        in_wishlist = False
        message = 'Removed from wishlist'
    except Wishlist.DoesNotExist:
        Wishlist.objects.create(user=request.user, product=product)
        in_wishlist = True
        message = 'Added to wishlist'

    wishlist_count = Wishlist.objects.filter(user=request.user).count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'in_wishlist': in_wishlist,
            'wishlist_count': wishlist_count,
            'message': message
        })

    return redirect(request.META.get('HTTP_REFERER', 'store:shop'))

@login_required
def razorpay_payment(request):
    cart = request.session.get('cart_snapshot')
    if not cart:
        messages.error(request, "Invalid payment session")
        return redirect('store:cart_detail')

    total = 0
    for pid, qty in cart.items():
        product = Product.objects.get(id=pid)
        total += product.price * qty

    client = razorpay.Client(auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    ))

    razorpay_order = client.order.create({
        "amount": int(total * 100),  # paise
        "currency": "INR",
        "payment_capture": 1
    })

    return render(request, 'store/razorpay.html', {
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'order_id': razorpay_order['id'],
        'amount': total
    })

@api_view(['POST'])
def verify_payment(request):
    client = razorpay.Client(auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    ))

    data = request.data

    # Verify signature
    try:
        client.utility.verify_payment_signature({
            'razorpay_payment_id': data.get('razorpay_payment_id'),
            'razorpay_order_id': data.get('razorpay_order_id'),
            'razorpay_signature': data.get('razorpay_signature'),
        })
    except SignatureVerificationError:
        return Response({'success': False, 'error': 'Signature verification failed'}, status=400)

    # Get session data
    cart = request.session.get('cart_snapshot')
    checkout_data = request.session.get('checkout_data')

    if not cart or not checkout_data:
        return Response({'success': False, 'error': 'Session expired'}, status=400)

    # Create order
    with transaction.atomic():
        order = Order.objects.create(
            user=request.user,
            full_name=checkout_data.get('full_name'),
            email = checkout_data.get('email') or request.user.email,
            phone=checkout_data.get('phone'),
            address=checkout_data.get('address'),
            city=checkout_data.get('city'),
            pincode=checkout_data.get('pincode'),
            notes=checkout_data.get('notes'),

            payment_method='razorpay',
            payment_status='paid',
            razorpay_order_id=data.get('razorpay_order_id'),
            razorpay_payment_id=data.get('razorpay_payment_id'),
            razorpay_signature=data.get('razorpay_signature'),
        )

        for pid, qty in cart.items():
            product = Product.objects.get(id=pid)
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=qty,
                price=product.price
            )

        # Clear cart + session
        request.session['cart'] = {}
        request.session.pop('cart_snapshot', None)
        request.session.pop('checkout_data', None)

    try:
        send_order_receipt(order)
        print("Receipt email sent to:", order.email)
    except Exception as e:
        print("Receipt email FAILED:", e)

    return Response({
        'success': True,
        'redirect_url': reverse('store:order_success', args=[order.id])
    })


@api_view(['POST'])
def send_otp(request):
    email = request.data.get('email')

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'Email not registered'}, status=400)

    otp = generate_otp()
    PasswordResetOTP.objects.create(user=user, otp=otp)

    send_mail(
        subject='KEC Password Reset OTP',
        message=f'Your OTP is {otp}. Valid for 10 minutes.',
        from_email=None,
        recipient_list=[email],
    )

    return Response({'message': 'OTP sent successfully'})

@api_view(['POST'])
def verify_otp(request):
    email = request.data.get('email')
    otp = request.data.get('otp')

    try:
        user = User.objects.get(email=email)
        otp_obj = PasswordResetOTP.objects.filter(
            user=user,
            otp=otp,
            is_verified=False
        ).last()
    except:
        return Response({'error': 'Invalid OTP'}, status=400)

    if otp_obj.is_expired():
        return Response({'error': 'OTP expired'}, status=400)

    otp_obj.is_verified = True
    otp_obj.save()

    return Response({
        'message': 'OTP verified',
        'token': str(otp_obj.token)
    })



@api_view(['POST'])
def reset_password(request):
    token = request.data.get('token')
    new_password = request.data.get('password')

    try:
        otp_obj = PasswordResetOTP.objects.get(token=token, is_verified=True)
    except PasswordResetOTP.DoesNotExist:
        return Response({'error': 'Invalid token'}, status=400)

    user = otp_obj.user
    user.password = make_password(new_password)
    user.save()

    otp_obj.delete()  # One-time use

    return Response({'message': 'Password reset successful'})

def forgot_password_page(request):
    return render(request, 'store/forgot_password.html')

def verify_otp_page(request):
    return render(request, 'store/verify_otp.html')

def reset_password_page(request):
    return render(request, 'store/reset_password.html')