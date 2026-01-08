from store.models import Product

def recommend_pumps(depth_ft, usage_type, phase, max_budget=None):
    """
    Rule-based recommendation logic
    """

    qs = Product.objects.filter(
        is_available=True,
        usage_type=usage_type,
        phase=phase,
        max_depth_ft__gte=depth_ft
    )

    if max_budget:
        qs = qs.filter(price__lte=max_budget)

    # Ranking logic (best first)
    qs = qs.order_by(
        'price',             # cheaper first
        '-motor_power_hp',   # higher power preferred
        '-max_flow_lpm'      # higher flow preferred
    )

    return qs
