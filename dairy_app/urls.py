from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='dairy_app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),
    
    # Area URLs
    path('areas/', views.AreaListView.as_view(), name='area_list'),
    path('areas/add/', views.AreaCreateView.as_view(), name='area_add'),
    path('areas/<int:pk>/edit/', views.AreaUpdateView.as_view(), name='area_edit'),
    path('areas/<int:pk>/delete/', views.AreaDeleteView.as_view(), name='area_delete'),
    path('areas/<int:pk>/customers/', views.area_customers_view, name='area_customers'),
    
    # Milk Type URLs
    path('milk-types/', views.MilkTypeListView.as_view(), name='milk_type_list'),
    path('milk-types/add/', views.MilkTypeCreateView.as_view(), name='milk_type_add'),
    path('milk-types/<int:pk>/edit/', views.MilkTypeUpdateView.as_view(), name='milk_type_edit'),
    path('milk-types/<int:pk>/delete/', views.MilkTypeDeleteView.as_view(), name='milk_type_delete'),
    
    # Customer URLs
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/add/', views.CustomerCreateView.as_view(), name='customer_add'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_edit'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    path('search-customers/', views.search_customers, name='search_customers'),
    path('ajax/update-customer-order/', views.update_customer_order, name='update_customer_order'),
    
    # Sale URLs
    path('sales/', views.SaleListView.as_view(), name='sale_list'),
    path('sales/add/', views.sale_create_view, name='sale_add'),
    path('sales/<int:pk>/edit/', views.SaleUpdateView.as_view(), name='sale_edit'),
    path('sales/<int:pk>/delete/', views.SaleDeleteView.as_view(), name='sale_delete'),
    path('ajax/get-milk-types/', views.get_milk_types_for_customer, name='get_milk_types_for_customer'),
    path('ajax/get-all-milk-types/', views.get_all_milk_types, name='get_all_milk_types'),
    
    # Payment URLs
    path('payments/', views.PaymentListView.as_view(), name='payment_list'),
    path('payments/add/', views.payment_create_view, name='payment_add'),
    path('payments/<int:pk>/edit/', views.PaymentUpdateView.as_view(), name='payment_edit'),
    path('payments/<int:pk>/delete/', views.PaymentDeleteView.as_view(), name='payment_delete'),
    
    # Report URLs
    path('reports/customer-export/', views.customer_export_view, name='customer_export'),
    path('reports/customer-export/download/', views.download_customer_data, name='download_customer_data'),
    
    # Bill Generation URLs
    path('customers/<int:pk>/bill/', views.generate_customer_bill, name='generate_customer_bill'),
]