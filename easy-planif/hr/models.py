from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from accounts.models import CustomUser

class Employee(models.Model):
    """
    Représente le profil d'un utilisateur de l'application.

    Un Employee est associé à un seul CustomUser via une relation OneToOneField.
    Le modèle contient les informations nécessaires à la gestion administrative
    et salariale d'un employé.

    Attributes:
        user: Utilisateur Django associé à l'employé.
        employee_number: Identifiant unique de l'employé.
        hourly_rate: Taux horaire de l'employé.
        monthly_salary: Salaire mensuel éventuel de l'employé.
        hired_on: Date d'entrée de l'employé.
        left_on: Date de départ de l'employé.
        is_active: Indique si l'employé est actuellement actif.
    """

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="employee_profile",
    )
    employee_number = models.CharField(
        max_length=30,
        unique=True,
    )
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal(0))],
    )
    monthly_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal(0))],
    )
    hired_on = models.DateField()
    left_on = models.DateField(
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        """
        Configuration du modèle Employee.

        Les employés sont triés par numéro d'employé par défaut.
        """

        ordering = ["employee_number"]

    def clean(self):
        """
        Effectue les validations métier du modèle.

        Vérifie que la date de départ de l'employé, lorsqu'elle est définie,
        n'est pas antérieure à sa date d'embauche.

        Raises:
            ValidationError: Si `left_on` est antérieure à `hired_on`.
        """
        super().clean()

        if self.left_on and self.left_on < self.hired_on:
            raise ValidationError(
                {
                    "left_on": (
                        "The end date cannot be before the hire date."
                    )
                }
            )

    def save(self, *args, **kwargs):
        """
        Valide l'instance avant de l'enregistrer en base de données.

        `full_clean()` exécute les validations Django, y compris la méthode
        `clean()` définie ci-dessus.

        Args:
            *args: Arguments positionnels transmis à la méthode `save()` de Django.
            **kwargs: Arguments nommés transmis à la méthode `save()` de Django.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Retourne une représentation lisible de l'employé.

        Returns:
            str: Le numéro de l'employé suivi de son utilisateur associé.

        Example:
            "EMP001 - Augustin Dupont"
        """
        return f"{self.employee_number} - {self.user}"