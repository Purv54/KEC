from django import forms
from store.models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'category',
            'name',
            'slug',
            'model_number',
            'description',
            'image',
            'price',
            'stock',
            'is_available',
            'motor_power_hp',
            'max_head_m',
            'max_flow_lpm',
            'max_depth_ft',
            'phase',
            'usage_type',
        ]

        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
