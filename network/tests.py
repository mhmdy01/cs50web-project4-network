from django.test import TestCase, Client
from django.db.models import Max

from .models import User, Post


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

class PostTests(TestCase):
    def setUp(self):
        """Create new user and posts in db"""
        self.credentials = { 'username': 'foo',  'password': 'foo' }
        self.post_to_add = {'content': 'new content'}

        u = User.objects.create_user(**self.credentials)
        Post.objects.create(content='post foo', user=u)
        Post.objects.create(content='post bar', user=u)
        Post.objects.create(content='post baz', user=u)

    def test_user_posts_count(self):
        """Check that the number of posts created by a user is correct"""
        # this wouldn't work if other testcases running?
        # (because they too create users)
        u = User.objects.get(pk=1)
        # u = User.objects.get(username=self.credentials['username'])

        self.assertEqual(u.posts.count(), 3)

    def test_index_page(self):
        """Should list correct number of posts"""
        c = Client()
        response = c.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['posts'].count(), 3)

    def test_create_post_fails_unauthorized(self):
        """Check that creating a post fails if current user isn't authorized"""
        c = Client()
        response = c.post('/posts/create', self.post_to_add)

        self.assertEqual(response.status_code, 401)

    def test_create_post_fails_notallowed(self):
        """Check that creating a post fails if request issued isn't POST"""
        c = Client()
        # must login first
        c.login(**self.credentials)
        response = c.get('/posts/create')

        self.assertEqual(response.status_code, 405)

    def test_create_post_works(self):
        """Check that an authorized user can create posts"""
        total_before = Post.objects.count()
        
        c = Client()
        # must login first
        c.login(**self.credentials)
        response = c.post('/posts/create', self.post_to_add, follow=True)

        # POV: views/templates/response
        self.assertEqual(response.status_code, 200)

        # POV: db state
        total_after = Post.objects.count()
        self.assertEqual(total_after, total_before + 1)

    def test_edit_post_fails_unauthorized(self):
        """Check that editing a post fails if current user isn't logged in"""
        p = Post.objects.get(pk=1)
        content = self.post_to_add['content'] + ' updated...!!!'

        c = Client()
        response = c.put(f'/posts/{p.id}/edit', {'content': content})

        self.assertEqual(response.status_code, 401)
    
    def test_edit_post_fails_notallowed(self):
        """Check that editing a post fails if request method isn't PUT"""
        p = Post.objects.get(pk=1)
        content = self.post_to_add['content'] + ' updated...!!!'

        # MUST LOGIN FIRST
        c = Client()
        c.login(**self.credentials)
        response = c.post(f'/posts/{p.id}/edit', {'content': content})

        self.assertEqual(response.status_code, 405)

    def test_edit_post_fails_notexist(self):
        """Check that editing a post fails if post doesn't exist in db"""
        max_id = Post.objects.all().aggregate(Max('id')).get('id__max')
        content = self.post_to_add['content'] + ' updated...!!!'

        # MUST LOGIN FIRST
        c = Client()
        c.login(**self.credentials)

        response = c.put(f'/posts/{max_id + 1}/edit', {'content': content})

        self.assertEqual(response.status_code, 404)
    
    def test_edit_post_fails_notowner(self):
        """Check that editing a post fails if current user isn't post owner"""
        p = Post.objects.get(pk=1)
        content = self.post_to_add['content'] + ' updated...!!!'

        # MUST LOGIN FIRST (BUT USING DIFFERENT CREDENTIALS)
        # MANALLY FOR NOW BECAUSE EDITING (setUp method) WOULD BREAK OTHER TESTS
        # TODO/refactor: update setUp and other tests
        c = Client()
        credentials = {'username': 'bar', 'password': 'bar'}
        User.objects.create_user(**credentials)
        c.login(**credentials)

        response = c.put(f'/posts/{p.id}/edit', {'content': content})

        self.assertEqual(response.status_code, 401)

    def test_edit_post_works(self):
        """Check that logged in users can edit their own posts"""
        p = Post.objects.get(pk=1)
        content = self.post_to_add['content'] + ' updated...!!!'

        # MUST LOGIN FIRST
        c = Client()
        c.login(**self.credentials)

        # PUT requests need a content-type header
        # since you're sending (and your server is expecting) json data
        # which is different form default (x=a&y=b...)
        response = c.put(f'/posts/{p.id}/edit', {"content": content}, content_type='application/json')

        # POV: response/template/view
        self.assertEqual(response.status_code, 200)

        # POV: db
        self.assertEqual(Post.objects.get(pk=1).content, content)

class UserProfile(TestCase):
    def setUp(self):
        """Create new user and posts in db"""
        self.credentials = { 'username': 'foo',  'password': 'foo' }

        u = User.objects.create_user(**self.credentials)
        Post.objects.create(content='post foo', user=u)
        Post.objects.create(content='post bar', user=u)
        Post.objects.create(content='post baz', user=u)

    def test_valid_profile_page(self):
        """Check that there's a profile page for a valid username"""
        c = Client()
        response = c.get(f'/{self.credentials["username"]}')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].username, self.credentials['username'])
        self.assertEqual(response.context['posts'].count(), 3)

    def test_invalid_profile_page(self):
        """Check that there's no profile page for an invalid username"""
        c = Client()
        response = c.get(f'/{self.credentials["username"] + "s"}')

        self.assertEqual(response.status_code, 404)

class UserFriendsFollowers(TestCase):
    def setUp(self):
        """add some users to db and make them follow each other"""
        self.foo_credentials = { 'username': 'foo',  'password': 'foo' }
        self.bar_credentials = { 'username': 'bar',  'password': 'bar' }
        self.baz_credentials = { 'username': 'baz',  'password': 'baz' }
        foo = User.objects.create_user(**self.foo_credentials)
        bar = User.objects.create_user(**self.bar_credentials)
        baz = User.objects.create_user(**self.baz_credentials)

        # when foo follows bar
        # bar is a friend to foo, foo is a follower to bar
        foo.friends.add(bar)
        bar.followers.add(foo)

        # when baz follows bar
        # bar is a friend to baz, baz is a follower to bar
        baz.friends.add(bar)
        bar.followers.add(baz)

    def test_friends_followers_relation_when_follow(self):
        """Check that when user A follows user B, user A friends count increases and
        User B followers count increases."""
        foo = User.objects.get(username='foo')
        bar = User.objects.get(username='bar')
        baz = User.objects.get(username='baz')

        self.assertEqual(foo.friends.count(), 1)    #bar
        self.assertEqual(baz.friends.count(), 1)    #bar
        self.assertEqual(bar.friends.count(), 0)
        self.assertEqual(foo.followers.count(), 0)
        self.assertEqual(baz.followers.count(), 0)
        self.assertEqual(bar.followers.count(), 2)  #foo, bar

    def test_friends_followers_relation_when_unfollow(self):
        """Check that when user A unfollows user B, user A friends count decreases and
        User B followers count decreases."""
        foo = User.objects.get(username='foo')
        bar = User.objects.get(username='bar')

        foo.friends.remove(bar)
        bar.followers.remove(foo)

        self.assertEqual(foo.friends.count(), 0)
        self.assertEqual(bar.followers.count(), 1)  # baz

    def test_follow_fails_notloggedin(self):
        """Check that following a user fails if current user isn't logged-in"""
        user_to_follow = User.objects.get(username='bar')

        c = Client()
        response = c.post(f'/{user_to_follow.username}/follow')

        self.assertEqual(response.status_code, 401)

    def test_follow_fails_notexist(self):
        """Check that following a user fails if user_to_follow doesn't exist in db"""
        user_to_follow = User.objects.get(username='bar')
        username = user_to_follow.username + 'i_dont_exist'

        c = Client()
        # must log in first
        c.login(**self.foo_credentials)
        response = c.post(f'/{username}/follow')

        self.assertEqual(response.status_code, 404)

    def test_follow_fails_isself(self):
        """Check that following a user fails if user_to_follow is same as current user"""
        user_to_follow = User.objects.get(username='foo')

        c = Client()
        # must log in first
        c.login(**self.foo_credentials)
        response = c.post(f'/{user_to_follow.username}/follow')

        self.assertEqual(response.status_code, 400)

    def test_follow_fails_alreadyfollowing(self):
        """Check that following a user fails if user_to_follow is already followed by current user"""
        current_user = User.objects.get(username='foo')
        user_to_follow = User.objects.get(username='bar')

        c = Client()
        # must log in first
        c.login(**self.foo_credentials)
        response = c.post(f'/{user_to_follow.username}/follow')

        self.assertEqual(response.status_code, 400)

    def test_follow_works(self):
        """Check that logged-in users can follow other users"""
        current_user = User.objects.get(username='bar')
        user_to_follow = User.objects.get(username='foo')

        c = Client()
        # must log in first
        c.login(**self.bar_credentials)
        response = c.post(f'/{user_to_follow.username}/follow')

        # pov: response/view/context
        self.assertEqual(response.status_code, 200)

        # pov: db
        self.assertEqual(current_user.friends.count(), 1)
        self.assertEqual(user_to_follow.followers.count(), 1)
