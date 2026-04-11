# terrains/admin.py
from django.contrib import admin
from .models import Terrain, Equipment, TerrainPhoto, TerrainEquipment, OpeningHours, MaintenancePeriod, Review

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name', 'description')

class TerrainPhotoInline(admin.TabularInline):
    model = TerrainPhoto
    extra = 1

class TerrainEquipmentInline(admin.TabularInline):
    model = TerrainEquipment
    extra = 1

class OpeningHoursInline(admin.TabularInline):
    model = OpeningHours
    extra = 1

class MaintenancePeriodInline(admin.TabularInline):
    model = MaintenancePeriod
    extra = 1

@admin.register(Terrain)
class TerrainAdmin(admin.ModelAdmin):
    list_display = ('name', 'terrain_type', 'capacity', 'price_per_hour', 'status', 'average_rating')
    list_filter = ('terrain_type', 'status')
    search_fields = ('name', 'description')
    list_editable = ('status', 'price_per_hour')
    readonly_fields = ('created_at', 'updated_at', 'average_rating')
    inlines = [TerrainPhotoInline, TerrainEquipmentInline, OpeningHoursInline, MaintenancePeriodInline]
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'description', 'terrain_type')
        }),
        ('Détails', {
            'fields': ('capacity', 'price_per_hour', 'status', 'average_rating')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

@admin.register(TerrainPhoto)
class TerrainPhotoAdmin(admin.ModelAdmin):
    list_display = ('terrain', 'caption', 'is_primary', 'order')
    list_filter = ('is_primary', 'terrain')
    search_fields = ('caption', 'terrain__name')

@admin.register(TerrainEquipment)
class TerrainEquipmentAdmin(admin.ModelAdmin):
    list_display = ('terrain', 'equipment', 'quantity', 'condition')
    list_filter = ('condition', 'equipment', 'terrain')
    search_fields = ('terrain__name', 'equipment__name')

@admin.register(OpeningHours)
class OpeningHoursAdmin(admin.ModelAdmin):
    list_display = ('terrain', 'day_of_week', 'opening_time', 'closing_time', 'is_closed')
    list_filter = ('day_of_week', 'is_closed', 'terrain')

@admin.register(MaintenancePeriod)
class MaintenancePeriodAdmin(admin.ModelAdmin):
    list_display = ('terrain', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'terrain')
    search_fields = ('terrain__name', 'reason')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('terrain', 'user', 'rating', 'is_approved', 'created_at')
    list_filter = ('rating', 'is_approved', 'terrain')
    search_fields = ('terrain__name', 'user__get_full_name', 'comment')
    list_editable = ('is_approved',)