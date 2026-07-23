# gather/users/forms.py
from allauth.account.forms import SignupForm
from django import forms
from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User
        field_classes = {"email": forms.EmailField}


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin. Subclasses the UserCreationForm to
    provide a Meta class using our custom User model.
    """

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        fields = ("email",)
        field_classes = {"email": forms.EmailField}
        error_messages = {
            "email": {"unique": _("This email has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """


class UserSocialSignupForm(SignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """


class AdminCreateUserForm(forms.Form):
    """
    Formulaire de création manuelle d'un utilisateur par un admin.
    Ne mappe PAS directement sur User (ModelForm) car les champs varient
    selon le rôle choisi (matricule pour étudiant, club pour organisateur).
    """

    email = forms.EmailField(label=_("Email"))
    first_name = forms.CharField(label=_("Prénom"), max_length=150)
    last_name = forms.CharField(label=_("Nom"), max_length=150)
    role = forms.ChoiceField(label=_("Rôle"), choices=User.Role.choices)

    # Champs spécifiques Étudiant (optionnels selon le rôle)
    matricule = forms.CharField(label=_("Matricule"), max_length=30, required=False)
    filiere = forms.CharField(label=_("Filière"), max_length=150, required=False)
    departement = forms.CharField(
        label=_("Département"),
        max_length=150,
        required=False,
    )
    niveau_etude = forms.CharField(
        label=_("Niveau d'étude"),
        max_length=20,
        required=False,
    )
    promotion = forms.CharField(label=_("Promotion"), max_length=9, required=False)

    # Champs spécifiques Organisateur (optionnels selon le rôle)
    club = forms.CharField(
        label=_("Club / Association"),
        max_length=255,
        required=False,
    )
    poste = forms.ChoiceField(label=_("Poste"), required=False, choices=[("", "---")])
    date_debut_mandat = forms.DateField(
        label=_("Date de prise de fonction"),
        required=False,
    )

    def clean(self):
        """Validation croisée : les champs requis dépendent du rôle choisi."""
        cleaned_data = super().clean()
        role = cleaned_data.get("role")

        if role == User.Role.ETUDIANT and not cleaned_data.get("matricule"):
            self.add_error("matricule", _("Le matricule est requis pour un étudiant."))

        if role == User.Role.ORGANISATEUR:
            if not cleaned_data.get("club"):
                self.add_error("club", _("Le club est requis pour un organisateur."))
            if not cleaned_data.get("date_debut_mandat"):
                self.add_error(
                    "date_debut_mandat",
                    _("La date de prise de fonction est requise."),
                )

        return cleaned_data


class AdminImportUsersCSVForm(forms.Form):
    """Formulaire d'upload pour l'import en masse d'utilisateurs via CSV."""

    fichier_csv = forms.FileField(
        label=_("Fichier CSV"),
        help_text=_("Colonnes attendues : email, first_name, last_name, role"),
    )

    def clean_fichier_csv(self):
        fichier = self.cleaned_data["fichier_csv"]
        if not fichier.name.endswith(".csv"):
            raise forms.ValidationError(_("Le fichier doit être au format .csv"))
        return fichier
