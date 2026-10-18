from datetime import datetime, timedelta
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

class WorkEntry(models.Model):
    """
    Représente une période de travail effectuée par un employé.

    Un WorkEntry est associé à un Employee et contient les informations
    nécessaires au suivi du temps de travail : date, heures de début et de fin,
    durée de pause, statut de validation, notes éventuelles et utilisateur
    ayant approuvé l'entrée.

    La durée effective de travail peut être obtenue via la propriété
    `duration_hours`. Le modèle effectue également des validations afin de
    garantir la cohérence des horaires et de la durée de pause.

    Attributes:
        employee: Employé associé à l'entrée de travail.
        work_date: Date à laquelle le travail a été effectué.
        start_time: Heure de début du travail.
        end_time: Heure de fin du travail.
        break_minutes: Durée de la pause en minutes.
        status: Statut de validation de l'entrée de travail.
        notes: Notes ou informations complémentaires associées à l'entrée.
        approved_by: Utilisateur ayant approuvé l'entrée de travail.
    """

    class Status(models.TextChoices):
        """
        Définit les différents statuts possibles d'une entrée de travail.
        """

        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="work_entries",
    )
    work_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_minutes = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="approved_work_entries",
    )

    class Meta:
        """
        Configuration du modèle WorkEntry.

        Les entrées sont triées par date de travail décroissante, puis par
        heure de début croissante.

        Une contrainte d'unicité empêche un employé d'avoir plusieurs entrées
        commençant à la même heure le même jour.
        """

        ordering = ["-work_date", "start_time"]

        constraints = [
            models.UniqueConstraint(
                fields=["employee", "work_date", "start_time"],
                name="unique_employee_work_entry_start",
            ),
        ]

    def clean(self):
        """
        Effectue les validations métier du modèle.

        Vérifie que :
        - l'heure de fin est strictement postérieure à l'heure de début ;
        - la durée de pause est strictement inférieure à la durée totale
          de la période de travail.

        Raises:
            ValidationError: Si les horaires ou la durée de pause sont invalides.
        """
        super().clean()

        if self.end_time <= self.start_time:
            raise ValidationError(
                {
                    "end_time": (
                        "The end time must be after the start time."
                    )
                }
            )

        duration = datetime.combine(
            self.work_date,
            self.end_time,
        ) - datetime.combine(
            self.work_date,
            self.start_time,
        )

        if self.break_minutes >= duration.total_seconds() / 60:
            raise ValidationError(
                {
                    "break_minutes": (
                        "The break must be shorter than the work duration."
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

    @property
    def duration_hours(self):
        """
        Retourne la durée effective de travail en heures.

        La durée est calculée à partir de l'heure de début et de l'heure de fin,
        puis diminuée de la durée de pause.

        La valeur retournée est arrondie à deux décimales.

        Returns:
            Decimal: Durée effective de travail en heures.

        Example:
            Pour une période de 08:00 à 17:00 avec une pause d'une heure,
            retourne `Decimal("8.00")`.
        """
        duration = datetime.combine(
            self.work_date,
            self.end_time,
        ) - datetime.combine(
            self.work_date,
            self.start_time,
        )

        duration -= timedelta(minutes=self.break_minutes)

        return Decimal(
            str(duration.total_seconds() / 3600)
        ).quantize(
            Decimal("0.01")
        )

    def __str__(self):
        """
        Retourne une représentation lisible de l'entrée de travail.

        Returns:
            str: L'employé associé suivi de la date de travail.

        Example:
            "EMP001 - 2026-10-08"
        """
        return f"{self.employee} - {self.work_date}"