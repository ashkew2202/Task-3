from django import forms
from django.contrib.auth import get_user_model
from .models import UserProfile, College, Player, Sport
from django.db import IntegrityError

CustomBaseUser = get_user_model()

class UserRegistrationForm(forms.Form):
    name = forms.CharField(max_length=100, required=True, label="Full Name")
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    gender = forms.ChoiceField(choices=[("Male", "Male"), ("Female", "Female")], required=True)
    password1 = forms.CharField(widget=forms.PasswordInput, required=True, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, required=True, label="Confirm Password")

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if CustomBaseUser.objects.filter(username=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        data = super().clean()
        p1 = data.get("password1")
        p2 = data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        return data

    def save(self):
        if not self.is_valid():
            return None
        email = self.cleaned_data["email"]
        try:
            user = CustomBaseUser.objects.create_user(
                username=email,
                email=email,
                password=self.cleaned_data["password1"]
            )
            UserProfile.objects.create(
                auth_user=user,
                name=self.cleaned_data["name"],
                phone_number=self.cleaned_data["phone_number"],
                gender=self.cleaned_data["gender"]
            )
        except IntegrityError:
            self.add_error("email", "Email just registered. Try login.")
            return None
        if hasattr(user, "user_type"):
            user.user_type = "player"
            user.save()
        return user

CustomBaseUser = get_user_model()

class PlayerRegistrationForm(forms.ModelForm):
    # Fields that aren’t in CustomBaseUser but needed for Player
    college = forms.ModelChoiceField(queryset=College.objects.all(), required=True)
    is_coach = forms.BooleanField(required=False, label="Register as Coach?")
    sports_if_coach = forms.ModelChoiceField(
        queryset=Sport.objects.all(),
        required=False,
        label="Sport (required if coach)"
    )

    def clean(self):
        cleaned = super().clean()
        college = cleaned.get("college")
        is_coach = cleaned.get("is_coach")
        sport = cleaned.get("sports_if_coach")
        if is_coach and sport and self.user:
            try:
                player_gender = UserProfile.objects.get(auth_user=self.user).gender
            except UserProfile.DoesNotExist:
                self.add_error(None, "Associated user profile not found.")
            else:
                sport_gender = sport.gender
                if sport_gender:
                    if sport_gender!=player_gender:
                        self.add_error(
                            "sports_if_coach",
                            f"Selected sport is restricted to {sport_gender} players."
                        )
            
        if is_coach and not sport:
            self.add_error("sports_if_coach", "Select a sport if registering as coach.")
        if not is_coach:
            cleaned["sports_if_coach"] = None  # ensure not required when not a coach
        return cleaned

    class Meta:
        model = Player
        fields = [
            "college",
            "is_coach",
            "sports_if_coach",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)  # pass in logged-in CustomBaseUser
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        if not self.user:
            raise ValueError("PlayerRegistrationForm requires a user instance")
        player = super().save(commit=False)
        profile = UserProfile.objects.get(auth_user=self.user)
        player.name = profile.name    
        player.phone_number = profile.phone_number
        player.gender = profile.gender
        player.auth_user = self.user
        player.email = self.user.email
        player.status = "pcr_confirmed"  # For now

        if commit:
            player.save()
        return player
    
class PlayerLoginForm(forms.Form):
    email = forms.EmailField(label="Email", required=True)
    password = forms.CharField(widget=forms.PasswordInput, label="Password", required=True)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            UserModel = get_user_model()
            try:
                user = UserModel.objects.get(email=email)
            except UserModel.DoesNotExist:
                raise forms.ValidationError("Invalid email or password.")

            if not user.check_password(password):
                raise forms.ValidationError("Invalid email or password.")

            cleaned_data["user"] = user
        return cleaned_data

class SportsRegistrationForm(forms.Form):
    sport = forms.ModelChoiceField(queryset=Sport.objects.all(), required=True, label="Select Sport")

class AdminLoginForm(forms.Form):
    username = forms.CharField(label="Admin Username", required=True)
    password = forms.CharField(widget=forms.PasswordInput, label="Password", required=True)

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get("username")
        password = cleaned.get("password")

        if username and password:
            User = get_user_model()
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise forms.ValidationError("Invalid username or password.")

            if not user.is_active:
                raise forms.ValidationError("This account is inactive.")

            if not user.user_type == "admin":
                raise forms.ValidationError("You do not have admin access.")

            cleaned["user"] = user
        return cleaned