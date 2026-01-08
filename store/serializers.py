from rest_framework import serializers
from .models import Order,Product
from django.urls import reverse

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = "__all__"

class ProductRecommendationSerializer(serializers.ModelSerializer):
    product_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'slug',
            'name',
            'model_number',
            'price',
            'motor_power_hp',
            'max_head_m',
            'max_flow_lpm',
            'max_depth_ft',
            'phase',
            'usage_type',
            'product_url',
        ]

    def get_product_url(self, obj):
        try:
            return reverse('store:product_detail', kwargs={'slug': obj.slug})
        except Exception:
            return None