from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test

from store.models import Product,Order,OrderItem
from django.contrib.auth.models import User
from django.db.models import Count

from .forms import ProductForm

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from django.db.models import Sum,Count,F 
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from store.models import Order, OrderItem


def admin_login(request):
    # If already logged in and is admin, redirect to dashboard
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('adminpanel:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_staff:
            login(request, user)
            return redirect('adminpanel:dashboard')
        else:
            messages.error(request, "Invalid credentials or not an admin")

    return render(request, 'adminpanel/login.html')

def admin_logout(request):
    logout(request)
    return redirect('adminpanel:login')

def is_admin(user):
    return user.is_authenticated and user.is_staff


@login_required(login_url='adminpanel:login')
@user_passes_test(is_admin)
def dashboard(request):

    # 🔹 BASIC STATS
    total_products = Product.objects.count()
    total_users = User.objects.count()
    total_orders = Order.objects.count()

    recent_orders = Order.objects.order_by('-created_at')[:5]

    # 🔹 TOTAL REVENUE (ALL ORDERS)
    total_revenue = sum(order.total_amount for order in Order.objects.all())

    # 🔹 CATEGORY-WISE SALES ANALYSIS (DELIVERED ORDERS)
    category_sales = (
        OrderItem.objects
        .filter(order__status='delivered')
        .values(
            'product__category__name',
            'product__category'
        )
        .annotate(
            revenue=Sum(F('price') * F('quantity'))
        )
        .order_by('-revenue')
    )

    category_labels = []
    category_revenues = []

    for item in category_sales:
        # Works for BOTH FK & CharField category
        category_name = (
            item.get('product__category__name')
            or item.get('product__category')
            or 'Unknown'
        )

        category_labels.append(category_name)
        category_revenues.append(float(item['revenue'] or 0))

    # 🔹 FINAL CONTEXT
    context = {
        'total_products': total_products,
        'total_users': total_users,
        'total_orders': total_orders,
        'recent_orders': recent_orders,
        'total_revenue': total_revenue,

        # Category-wise chart data
        'category_labels': category_labels,
        'category_revenues': category_revenues,
    }

    return render(request, 'adminpanel/dashboard.html', context)

@login_required(login_url='adminpanel:login')
@user_passes_test(is_admin)
def product_list(request):
    products = Product.objects.all()

    # 🔍 SEARCH
    search_query = request.GET.get('q', '').strip()
    if search_query:
        products = products.filter(name__icontains=search_query)

    # 🔃 SORTING
    sort_by = request.GET.get('sort', '')

    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'stock_asc':
        products = products.order_by('stock')
    elif sort_by == 'stock_desc':
        products = products.order_by('-stock')
    else:
        products = products.order_by('-id')  # default: newest first

    # 📄 PAGINATION
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
    }

    return render(request, 'adminpanel/products/product_list.html', context)

@login_required(login_url='adminpanel:login')
@user_passes_test(is_admin)
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('adminpanel:product_list')
    else:
        form = ProductForm()

    return render(request, 'adminpanel/products/product_add.html', {
        'form': form
    })


@login_required(login_url='adminpanel:login')
@user_passes_test(is_admin)
def product_edit(request, id):
    product = get_object_or_404(Product, id=id)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('adminpanel:product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'adminpanel/products/product_edit.html', {
        'form': form,
        'product': product
    })


@login_required(login_url='adminpanel:login')
@user_passes_test(is_admin)
def product_delete(request, id):
    product = get_object_or_404(Product, id=id)
    product.delete()
    return redirect('adminpanel:product_list')

@login_required(login_url='adminpanel:login')
@user_passes_test(is_admin)
def order_list(request):
    orders_qs = Order.objects.select_related('user').order_by('-created_at')

    status_choices = [
        'Pending',
        'Confirmed',
        'Shipped',
        'Delivered',
        'Cancelled',
    ]

    # 🔍 SEARCH
    search_query = request.GET.get('q', '').strip()
    if search_query:
        orders_qs = orders_qs.filter(
            Q(id__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )

    # 🎯 STATUS FILTER
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        orders_qs = orders_qs.filter(status__iexact=status_filter)

    # 📄 PAGINATION (ALWAYS LAST)
    paginator = Paginator(orders_qs, 10)  # 10 orders per page
    page_number = request.GET.get('page')

    try:
        orders = paginator.page(page_number)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    return render(request, 'adminpanel/orders/order_list.html', {
        'orders': orders,
        'status_choices': status_choices,
        'search_query': search_query,
        'status_filter': status_filter,
    })


@login_required(login_url='adminpanel:login')
@user_passes_test(is_admin)
def order_detail(request, id):
    order = get_object_or_404(Order, id=id)
    items = OrderItem.objects.select_related('product').filter(order=order)

    status_choices = [
        'Pending',
        'Confirmed',
        'Shipped',
        'Delivered',
        'Cancelled',
    ]

    # 🔄 UPDATE STATUS
    if request.method == 'POST':
        new_status = request.POST.get('status')

        if new_status in status_choices:
            if order.status != new_status:
                order.status = new_status
                order.save()
                messages.success(
                    request,
                    f"Order #{order.id} status updated to {new_status}"
                )
        else:
            messages.error(request, "Invalid status selected")

        return redirect('adminpanel:order_detail', id=order.id)

    return render(request, 'adminpanel/orders/order_detail.html', {
        'order': order,
        'items': items,
        'status_choices': status_choices,
    })

@login_required(login_url='adminpanel:login')
@user_passes_test(is_admin)
def product_bulk_delete(request):
    if request.method == 'POST':
        product_ids = request.POST.getlist('product_ids')
        if product_ids:
            Product.objects.filter(id__in=product_ids).delete()
    return redirect('adminpanel:product_list')

@login_required(login_url='adminpanel:login')
@user_passes_test(is_admin)
def user_list(request):
    users = User.objects.all().annotate(
        total_orders=Count('order')
    ).order_by('-date_joined')

    # 🔍 SEARCH
    search_query = request.GET.get('q', '').strip()
    if search_query:
        users = users.filter(
            username__icontains=search_query
        )

    # 📄 PAGINATION
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'users': page_obj,
        'search_query': search_query,
    }

    return render(request, 'adminpanel/users/user_list.html', context)


@login_required(login_url='adminpanel:login')
@user_passes_test(is_admin)
def user_detail(request, id):
    user = get_object_or_404(User, id=id)

    orders = Order.objects.filter(user=user).order_by('-created_at')

    total_orders = orders.count()

    # ✅ Calculate total spent from OrderItem
    total_spent = OrderItem.objects.filter(
        order__user=user
    ).aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or 0

    context = {
        'user_obj': user,
        'orders': orders,
        'total_orders': total_orders,
        'total_spent': total_spent,
    }

    return render(request, 'adminpanel/users/user_detail.html', context)