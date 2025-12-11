# Generated manually for making User.corredora nullable

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='corredora',
            field=models.ForeignKey(
                blank=True,
                help_text='Corredora a la que pertenece el usuario (opcional para superusuarios)',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='usuarios',
                to='usuarios.corredora'
            ),
        ),
    ]
