from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0004_payrollpayment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workentry",
            name="break_minutes",
            field=models.PositiveIntegerField(default=30),
        ),
    ]
