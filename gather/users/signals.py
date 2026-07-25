from pathlib import Path

from django.db.models.signals import post_delete
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import User


def _supprimer_fichier(champ_fichier) -> None:
    """Supprime physiquement un fichier du système de fichiers s'il existe."""
    if not champ_fichier:
        return
    chemin = Path(champ_fichier.path)
    if chemin.is_file():
        chemin.unlink()


@receiver(post_delete, sender=User)
def supprimer_photo_a_suppression_utilisateur(sender, instance, **kwargs):
    """Supprime la photo de profil quand l'utilisateur est supprimé."""
    _supprimer_fichier(instance.photo)


@receiver(pre_save, sender=User)
def supprimer_ancienne_photo_au_remplacement(sender, instance, **kwargs):
    """Supprime l'ancienne photo quand elle est remplacée par une nouvelle."""
    if not instance.pk:
        return

    try:
        ancienne_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    ancienne_photo = ancienne_instance.photo
    nouvelle_photo = instance.photo

    if ancienne_photo and ancienne_photo != nouvelle_photo:
        _supprimer_fichier(ancienne_photo)
