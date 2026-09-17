import csv

from django.http import HttpResponse

from customers.models import Customer


def export_customers(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="customers.csv"'
    writer = csv.writer(response)
    writer.writerow(["name", "email", "notes"])
    for customer in Customer.objects.all():
        writer.writerow([customer.name, customer.email, customer.notes])
    return response
