from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from .models import Address

User = get_user_model()

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or Username",
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username or Email (e.g. kuxhagr)', 'autocomplete': 'username'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': '••••••••', 'autocomplete': 'current-password'})
    )


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Create strong password'})
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Repeat password'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'name@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 9876543210'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'customer'
        if commit:
            user.save()
        return user


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['title', 'address_line1', 'address_line2', 'city', 'pincode', 'latitude', 'longitude', 'is_default']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., Home / Work'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'House / Flat / Block No, Street'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Apartment / Landmark (Optional)'}),
            'city': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'City'}),
            'pincode': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '6-digit PIN code'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

