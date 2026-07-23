import django.utils.timezone
from django.db import migrations, models

import gather.users.models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="name",
        ),
        migrations.AddField(
            model_name="user",
            name="first_name",
            field=models.CharField(
                blank=True,
                max_length=150,
                verbose_name="Prénom",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="last_name",
            field=models.CharField(
                blank=True,
                max_length=150,
                verbose_name="Nom",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("etudiant", "Étudiant"),
                    ("organisateur", "Organisateur"),
                    ("admin", "Administrateur"),
                ],
                db_index=True,
                default="etudiant",
                max_length=20,
                verbose_name="Rôle",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="telephone",
            field=models.CharField(
                blank=True,
                max_length=20,
                validators=[gather.users.models.phone_validator],
                verbose_name="Téléphone",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="photo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="users/photos/%Y/%m/",
                verbose_name="Photo de profil",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="langue",
            field=models.CharField(
                choices=[("fr", "Français"), ("en", "English")],
                default="fr",
                max_length=10,
                verbose_name="Langue préférée",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="fuseau_horaire",
            field=models.CharField(
                default="Africa/Douala",
                max_length=50,
                verbose_name="Fuseau horaire",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                verbose_name="Dernière modification",
            ),
        ),
    ]
