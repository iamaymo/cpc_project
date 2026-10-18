from django.test import TestCase, Client
from django.urls import reverse
from .models import Clients, Engineers, Networks
from .forms import RegisterForm


class ModelsAndRegistrationTests(TestCase):
    def setUp(self):
        self.engineer = Engineers.objects.create(
            full_name='Eng. Mohammed',
            username='eng_moh',
            phone_number='0501234567',
            email='moh@example.com',
            number_of_networks=0,
        )

    def test_clients_and_engineers_models(self):
        client = Clients.objects.create(
            first_name='Ali',
            last_name='Salem',
            email='ali@example.com',
            username='ali_s',
            phone_number='0555555555',
        )
        self.assertEqual(str(client), 'Ali Salem (ali_s)')
        self.assertEqual(str(self.engineer), 'Eng. Mohammed')

    def test_multiple_networks_for_client_and_one_engineer(self):
        client = Clients.objects.create(
            first_name='Hassan',
            last_name='Ahmed',
            email='hassan@example.com',
            username='hassan_a',
            phone_number='0566666666',
        )
        network1 = Networks.objects.create(
            network_name='Network 1',
            owner=client,
            assigned_engineer=self.engineer,
        )
        network2 = Networks.objects.create(
            network_name='Network 2',
            owner=client,
            assigned_engineer=self.engineer,
        )

        # One client has multiple networks
        self.assertEqual(client.networks.count(), 2)
        self.assertIn(network1, client.networks.all())
        self.assertIn(network2, client.networks.all())

        # Each network has one assigned engineer
        self.assertEqual(network1.assigned_engineer, self.engineer)
        self.assertEqual(network2.assigned_engineer, self.engineer)

    def test_register_get_view(self):
        client = Client()
        response = client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'البيانات الشخصية')
        self.assertContains(response, 'بيانات الشبكة')
        self.assertContains(response, 'التالي')
        self.assertContains(response, 'السابق')

    def test_register_post_view_success(self):
        client = Client()
        post_data = {
            'first_name': 'Khaled',
            'last_name': 'Omar',
            'username': 'khaled_o',
            'phone_number': '0599999999',
            'email': 'khaled@example.com',
            'network_name': 'Khaled Fiber Net',
            'assigned_engineer': self.engineer.id,
        }
        response = client.post(reverse('register'), post_data)
        self.assertEqual(response.status_code, 302)

        # Check Client created
        new_client = Clients.objects.get(username='khaled_o')
        self.assertEqual(new_client.phone_number, '0599999999')

        # Check Network created
        network = Networks.objects.get(network_name='Khaled Fiber Net')
        self.assertEqual(network.owner, new_client)
        self.assertEqual(network.assigned_engineer, self.engineer)

        # Check Engineer's network count updated
        self.engineer.refresh_from_db()
        self.assertEqual(self.engineer.number_of_networks, 1)
