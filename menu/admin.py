from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html

from .models import ALLERGEN_CHOICES, Category, Dish


class DishAdminForm(forms.ModelForm):
    allergens = forms.MultipleChoiceField(
        choices=ALLERGEN_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Аллергены',
    )

    class Meta:
        model = Dish
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial['allergens'] = self.instance.get_allergens_list()

    def clean_allergens(self):
        codes = set(self.cleaned_data.get('allergens', []))
        return ','.join(code for code, name in ALLERGEN_CHOICES if code in codes)


class DishInline(admin.TabularInline):
    model = Dish
    extra = 0
    fields = ['name', 'price', 'weight', 'unit', 'is_available', 'is_featured', 'order']
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active', 'dishes_count']
    list_editable = ['order', 'is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [DishInline]

    @admin.display(description='Блюд')
    def dishes_count(self, obj):
        return obj.dishes.count()


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    form = DishAdminForm
    list_display = ['photo', 'name', 'category', 'price', 'weight_display', 'kitchen_station',
                    'is_available', 'is_featured', 'badges_list']
    list_display_links = ['photo', 'name']
    list_editable = ['price', 'is_available', 'is_featured']
    list_filter = ['category', 'kitchen_station', 'is_available', 'is_featured',
                   'is_new', 'is_hit', 'is_chef_choice', 'is_spicy', 'is_vegetarian']
    search_fields = ['name', 'description', 'ingredients']
    list_select_related = ['category']
    list_per_page = 30
    readonly_fields = ['photo_preview', 'created_at', 'updated_at']
    actions = ['add_to_stop_list', 'remove_from_stop_list', 'show_on_main_page']
    fieldsets = (
        ('Основное', {'fields': ('category', 'name', 'description', 'price', 'order')}),
        ('Фото', {'fields': ('image', 'photo_preview')}),
        ('Состав', {'fields': ('ingredients', 'allergens', 'weight', 'unit', 'calories')}),
        ('Кухня', {'fields': ('kitchen_station', 'cooking_time')}),
        ('Бейджи', {'fields': ('is_new', 'is_hit', 'is_chef_choice', 'is_spicy', 'is_vegetarian')}),
        ('Показ', {'fields': ('is_available', 'is_featured')}),
        ('Служебное', {'fields': ('created_at', 'updated_at')}),
    )

    @admin.display(description='Фото')
    def photo(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:50px;height:50px;object-fit:cover;border-radius:6px">', obj.image.url)
        return '-'

    @admin.display(description='Превью')
    def photo_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width:250px;border-radius:8px">', obj.image.url)
        return 'Фото не загружено'

    @admin.display(description='Вес')
    def weight_display(self, obj):
        return obj.weight_display

    @admin.display(description='Бейджи')
    def badges_list(self, obj):
        return ', '.join(badge['label'] for badge in obj.badges) or '-'

    @admin.action(description='Поставить в стоп-лист')
    def add_to_stop_list(self, request, queryset):
        count = queryset.update(is_available=False)
        self.message_user(request, f'В стоп-лист поставлено блюд: {count}', messages.SUCCESS)

    @admin.action(description='Вернуть в меню')
    def remove_from_stop_list(self, request, queryset):
        count = queryset.update(is_available=True)
        self.message_user(request, f'Вернули в меню блюд: {count}', messages.SUCCESS)

    @admin.action(description='Показывать на главной')
    def show_on_main_page(self, request, queryset):
        count = queryset.update(is_featured=True)
        self.message_user(request, f'На главной теперь блюд: {count}', messages.SUCCESS)