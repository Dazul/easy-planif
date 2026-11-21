from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0002_workentry"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="employee",
            name="monthly_salary",
        ),
    ]
