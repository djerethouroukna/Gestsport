# Migration pour ajouter le champ image à la table terrains
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('terrains', '0001_initial'),  # Remplacez par votre dernière migration
    ]

    operations = [
        migrations.AddField(
            model_name='terrain',
            name='image',
            field=models.URLField(
                max_length=500, 
                blank=True, 
                null=True,
                help_text="URL de l'image du terrain"
            ),
        ),
    ]

# Pour créer cette migration :
# python manage.py makemigrations terrains --name add_image_field
# python manage.py migrate
