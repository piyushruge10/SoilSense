from django import forms

from .models import SerialConfiguration


class SerialConfigurationForm(forms.ModelForm):
    class Meta:
        model = SerialConfiguration
        fields = ("baud_rate", "moisture_threshold", "sample_interval")
        widgets = {
            "baud_rate": forms.NumberInput(attrs={"min": 300, "max": 1000000}),
            "moisture_threshold": forms.NumberInput(attrs={"min": 0, "max": 100}),
            "sample_interval": forms.NumberInput(attrs={"min": 1, "max": 3600}),
        }
