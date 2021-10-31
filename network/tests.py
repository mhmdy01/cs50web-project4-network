from django.test import TestCase, Client

from .models import User


class UserLogin(TestCase):
    def setUp(self):
        """Create new user in db"""
        self.credentials = { 'username': 'foo',  'password': 'foo' }
        User.objects.create_user(**self.credentials)

    def test_login_success(self):
        """Check that login succeeds when user enters
        their correct username and password
        """
        c = Client()
        response = c.post('/login', self.credentials, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertEqual(response.context['user'].username, self.credentials['username'])

    def test_login_fail_username(self):
        """Check that login fails if user didn't enter their correct username"""
        self.credentials['username'] = self.credentials['username'].upper()

        c = Client()
        response = c.post('/login', self.credentials, follow=True)

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.context['user'].is_authenticated)
        self.assertEqual(response.context['message'], "Invalid username and/or password.")

    def test_login_fail_password(self):
        """Check that login fails if user didn't enter their correct password"""
        self.credentials['password'] = self.credentials['password'].upper()

        c = Client()
        response = c.post('/login', self.credentials, follow=True)

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.context['user'].is_authenticated)
        self.assertEqual(response.context['message'], "Invalid username and/or password.")

class UserLogout(TestCase):
    def setUp(self):
        """Create new user in db and log it in"""
        self.credentials = { 'username': 'foo',  'password': 'foo' }
        User.objects.create_user(**self.credentials)

        c = Client()
        self.response_before_logout = c.post('/login', self.credentials, follow=True)

    def test_logout_works(self):
        """Check that when user logs out their session isn't authenticated anymore"""
        c = Client()
        response_after_logout = c.get('/logout', follow=True)

        self.assertTrue(self.response_before_logout.context['user'].is_authenticated)
        self.assertEqual(response_after_logout.status_code, 200)
        self.assertFalse(response_after_logout.context['user'].is_authenticated)

class UserSignup(TestCase):
    def setUp(self):
        """Create new user to db and initialize some fields for another user signup"""
        self.credentials = { 'username': 'foo',  'password': 'foo' }
        User.objects.create_user(**self.credentials)

        self.form_fields = {
            'username': 'bar',
            'email': 'bar@email.com',
            'password': 'bar',
            'confirmation': 'bar'
        }

    def test_signup_success(self):
        """Check that signup succeeds when user enters
        unqiue username, unqiue email and a correct password twice
        """
        c = Client()
        response = c.post('/register', self.form_fields, follow=True)

        # POV: views/templates/response
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertEqual(response.context['user'].username, self.form_fields['username'])

        # POV: db state
        self.assertEqual(User.objects.count(), 2)

    def test_signup_fail_password(self):
        """Check that signup fails if user didn't enter a correct password twice"""
        self.form_fields['confirmation'] = self.form_fields['confirmation'].upper()

        c = Client()
        response = c.post('/register', self.form_fields, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['user'].is_authenticated)
        self.assertEqual(response.context['message'], "Passwords must match.")

    def test_signup_fail_username(self):
        """Check that signup fails if user didn't enter a unique username"""
        self.form_fields['username'] = self.credentials['username']

        c = Client()
        response = c.post('/register', self.form_fields, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['user'].is_authenticated)
        self.assertEqual(response.context['message'], "Username already taken.")
