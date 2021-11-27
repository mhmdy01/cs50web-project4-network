import math

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
        # self.assertEqual(response.context['posts'].count(), 3)

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

    def test_post_ordering_correct(self):
        """Check that most recent posts always appear first"""
        first_post = Post.objects.first()
        self.assertEqual(first_post._meta.ordering[0], '-created_at')

class EditPostTests(TestCase):
    def setUp(self):
        """Add two users and a post to db"""
        # config db
        # db: create two users
        foo_credentials = { 'username': 'foo',  'password': 'foo' }
        bar_credentials = { 'username': 'bar',  'password': 'bar' }
        foo = User.objects.create_user(**foo_credentials)
        bar = User.objects.create_user(**bar_credentials)

        # db: create a post
        p = Post.objects.create(content='some content', user=foo)

        # config client/server
        # instantiate
        self.client = Client()

        # client: identify users (and their login credentials)
        self.user_who_created_post = foo
        self.login_credentials_of_user_who_created_post = foo_credentials

        self.user_who_didnt_create_post = bar
        self.login_credentials_of_user_who_didnt_create_post = bar_credentials

        # client: identify resources
        self.post_to_edit = p

    def test_edit_post_fails_notloggedin(self):
        """Check that editing a post fails if current user isn't logged in"""
        new_content = "some new content"

        response = self.client.put(f'/posts/{self.post_to_edit.id}/edit', {'content': new_content})
        self.assertEqual(response.status_code, 401)

    def test_edit_post_fails_notexist(self):
        """Check that editing a post fails if post doesn't exist in db"""
        new_content = "some new content"

        # must login first
        self.client.login(**self.login_credentials_of_user_who_created_post)

        response = self.client.put(f'/posts/{self.post_to_edit.id + 1014104}/edit', {'content': new_content})
        self.assertEqual(response.status_code, 404)

    def test_edit_post_fails_notowner(self):
        """Check that editing a post fails if current user isn't post owner"""
        new_content = "some new content"

        # must login first
        self.client.login(**self.login_credentials_of_user_who_didnt_create_post)

        response = self.client.put(f'/posts/{self.post_to_edit.id}/edit', {'content': new_content})
        self.assertEqual(response.status_code, 401)

    def test_edit_post_works(self):
        """Check that logged in users can edit their own posts"""
        new_content = "some new content"

        # must login first
        self.client.login(**self.login_credentials_of_user_who_created_post)

        # PUT requests need a content-type header
        # since you're sending (and your server is expecting) json data
        # which is different form default (x=a&y=b...)
        response = self.client.put(f'/posts/{self.post_to_edit.id}/edit', {'content': new_content}, content_type='application/json')

        # POV: response/template/view
        self.assertEqual(response.status_code, 200)
        # POV: db
        self.assertEqual(Post.objects.get(pk=1).content, new_content)

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
        """add some users to db and make some friend/follower relations"""
        # config db
        # db: create some users
        foo_credentials = { 'username': 'foo',  'password': 'foo' }
        bar_credentials = { 'username': 'bar',  'password': 'bar' }
        baz_credentials = { 'username': 'baz',  'password': 'baz' }
        foo = User.objects.create_user(**foo_credentials)
        bar = User.objects.create_user(**bar_credentials)
        baz = User.objects.create_user(**baz_credentials)

        # db: add some friends/followers
        # when foo follows bar
        # bar is a friend to foo, foo is a follower to bar
        foo.friends.add(bar)
        bar.followers.add(foo)

        # client/server config
        # instantiate
        self.client = Client()

        # client: identify users (current, to follow/unfollow) and their login credentials
        self.user_to_follow_and_unfollow = User.objects.get(username='bar')
        self.login_credentials_of_user_to_follow_and_unfollow = bar_credentials

        self.user_who_already_followed_user_to_follow_and_unfollow = foo
        self.login_credentials_of_user_who_already_followed_user_to_follow_and_unfollow = foo_credentials

        self.user_who_hadnt_followed_user_to_follow_and_unfollow = baz
        self.login_credentials_of_user_who_hadnt_followed_user_to_follow_and_unfollow = baz_credentials

    def test_friends_followers_relation_when_follow(self):
        """Check that when user A follows user B, user A friends count increases and
        User B followers count increases."""
        self.user_who_hadnt_followed_user_to_follow_and_unfollow.friends.add(self.user_to_follow_and_unfollow)
        self.user_to_follow_and_unfollow.followers.add(self.user_who_hadnt_followed_user_to_follow_and_unfollow)

        self.assertEqual(self.user_who_already_followed_user_to_follow_and_unfollow.friends.count(), 1)    #bar
        self.assertEqual(self.user_who_hadnt_followed_user_to_follow_and_unfollow.friends.count(), 1)      #bar
        self.assertEqual(self.user_to_follow_and_unfollow.followers.count(), 2)  #foo,baz

    def test_friends_followers_relation_when_unfollow(self):
        """Check that when user A unfollows user B, user A friends count decreases and
        User B followers count decreases."""
        self.user_who_already_followed_user_to_follow_and_unfollow.friends.remove(self.user_to_follow_and_unfollow)
        self.user_to_follow_and_unfollow.followers.remove(self.user_who_already_followed_user_to_follow_and_unfollow)

        self.assertEqual(self.user_who_already_followed_user_to_follow_and_unfollow.friends.count(), 0)
        self.assertEqual(self.user_to_follow_and_unfollow.followers.count(), 0)

    def test_follow_fails_notloggedin(self):
        """Check that following a user fails if current user isn't logged-in"""
        response = self.client.post(f'/{self.user_to_follow_and_unfollow.username}/follow')
        self.assertEqual(response.status_code, 401)

    def test_follow_fails_notexist(self):
        """Check that following a user fails if user_to_follow doesn't exist in db"""
        # must log in first
        self.client.login(**self.login_credentials_of_user_who_hadnt_followed_user_to_follow_and_unfollow)

        response = self.client.post(f'/{self.user_to_follow_and_unfollow.username + "i_dont_exist"}/follow')
        self.assertEqual(response.status_code, 404)

    def test_follow_fails_isself(self):
        """Check that following a user fails if user_to_follow is same as current user"""
        # must log in first
        self.client.login(**self.login_credentials_of_user_to_follow_and_unfollow)

        response = self.client.post(f'/{self.user_to_follow_and_unfollow.username}/follow')
        self.assertEqual(response.status_code, 400)

    def test_follow_fails_alreadyfollowing(self):
        """Check that following a user fails if user_to_follow is already followed by current user"""
        # must log in first
        self.client.login(**self.login_credentials_of_user_who_already_followed_user_to_follow_and_unfollow)

        response = self.client.post(f'/{self.user_to_follow_and_unfollow.username}/follow')
        self.assertEqual(response.status_code, 400)

    def test_follow_works(self):
        """Check that logged-in users can follow other users"""
        # must log in first
        self.client.login(**self.login_credentials_of_user_who_hadnt_followed_user_to_follow_and_unfollow)

        response = self.client.post(f'/{self.user_to_follow_and_unfollow.username}/follow', follow=True)
        # pov: response/view/context
        self.assertEqual(response.status_code, 200)
        # pov: db
        self.assertEqual(self.user_who_hadnt_followed_user_to_follow_and_unfollow.friends.count(), 1)    #bar
        self.assertEqual(self.user_to_follow_and_unfollow.followers.count(), 2)  #foo, baz

    def test_unfollow_fails_notloggedin(self):
        """Check that unfollowing a user fails if current user isn't logged-in"""
        response = self.client.post(f'/{self.user_to_follow_and_unfollow.username}/unfollow')
        self.assertEqual(response.status_code, 401)

    def test_unfollow_fails_notexist(self):
        """Check that ufollowing a user fails if user_to_unfollow doesn't exist in db"""
        # must log in first
        self.client.login(**self.login_credentials_of_user_who_already_followed_user_to_follow_and_unfollow)

        response = self.client.post(f'/{self.user_to_follow_and_unfollow.username + "i_dont_exist"}/unfollow')
        self.assertEqual(response.status_code, 404)

    def test_unfollow_fails_isself(self):
        """Check that unfollowing a user fails if user_to_unfollow is same as current user"""
        # must log in first
        self.client.login(**self.login_credentials_of_user_to_follow_and_unfollow)

        response = self.client.post(f'/{self.user_to_follow_and_unfollow.username}/unfollow')
        self.assertEqual(response.status_code, 400)

    def test_unfollow_fails_notfollowing(self):
        """Check that unfollowing a user fails if user_to_unfollow isn't already followed by current user"""
        # must log in first
        self.client.login(**self.login_credentials_of_user_who_hadnt_followed_user_to_follow_and_unfollow)

        response = self.client.post(f'/{self.user_to_follow_and_unfollow.username}/unfollow')
        self.assertEqual(response.status_code, 400)

    def test_unfollow_works(self):
        """Check that logged-in users can unfollow users they are following"""
        # must log in first
        self.client.login(**self.login_credentials_of_user_who_already_followed_user_to_follow_and_unfollow)

        response = self.client.post(f'/{self.user_to_follow_and_unfollow.username}/unfollow', follow=True)
        # pov: response/view/context
        self.assertEqual(response.status_code, 200)
        # pov: db
        self.assertEqual(self.user_who_already_followed_user_to_follow_and_unfollow.friends.count(), 0)
        self.assertEqual(self.user_to_follow_and_unfollow.followers.count(), 0)

class UserFriendsPostsTests(TestCase):
    def setUp(self):
        """Create new user and posts in db"""
        self.foo_credentials = { 'username': 'foo',  'password': 'foo' }
        self.bar_credentials = { 'username': 'bar',  'password': 'bar' }
        self.baz_credentials = { 'username': 'baz',  'password': 'baz' }

        # create some users
        foo = User.objects.create_user(**self.foo_credentials)
        bar = User.objects.create_user(**self.bar_credentials)
        baz = User.objects.create_user(**self.baz_credentials)

        # create some friends/followers
        foo.friends.add(bar)
        bar.followers.add(foo)

        foo.friends.add(baz)
        baz.followers.add(foo)

        # create some posts
        posts_to_add = [f'post #{i + 1}' for i in range(5)]
        for post_content in posts_to_add:
            Post.objects.create(content=post_content, user=bar)
            Post.objects.create(content=post_content, user=baz)

    def test_friends_posts_page_fails_notloggedin(self):
        """Check that visting friends post page fails if current user isn't logged-in"""
        c = Client()
        response = c.get('/following')

        self.assertEqual(response.status_code, 401)

    def test_friends_posts_page_works(self):
        """Check that logged-in users can visit a page to view the posts created by their friends"""
        # current_user = 'foo'
        # friends = 'bar', 'baz'

        c = Client()
        # must login first
        c.login(**self.foo_credentials)
        response = c.get('/following')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['posts'].count(), 10) # bar_posts + baz_posts

class PaginationTests(TestCase):
    def setUp(self):
        """add a new user and posts in db"""
        self.credentials = { 'username': 'foo',  'password': 'foo' }

        # create some users
        user = User.objects.create_user(**self.credentials)

        # create some posts
        self.posts_to_add = [f'post #{i + 1}' for i in range(55)]
        for post_content in self.posts_to_add:
            Post.objects.create(content=post_content, user=user)

        # pagination details
        # how many posts per page?
        self.page_size = 10

    def test_pagination_default_page(self):
        """Check that if no page (GET param) is specified, the current page defaults to 1"""
        c = Client()
        response = c.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].number, 1)

    def test_pagination_page_size_correct(self):
        """Check that each page lists 10 posts"""
        c = Client()
        response = c.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].__len__(), 10)

    def test_pagination_first_page_has_no_prev(self):
        """Check that the first page doesn't have a previous page"""
        c = Client()
        response = c.get('/?page=1')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['page'].has_previous())

    def test_pagination_last_page_has_no_next(self):
        """Check that the last page doesn't have a next page"""
        # what's last page?
        # ceil(total / page_size)
        last_page = math.ceil(len(self.posts_to_add) / self.page_size)

        c = Client()
        response = c.get(f'/?page={last_page}')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['page'].has_next())

    def test_pagination_next_page_correct(self):
        """Check that on some page (#n), the next page is what we expect (#n+1)"""
        current_page = 3

        c = Client()
        response = c.get(f'/?page={current_page}')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['page'].has_next())
        self.assertEqual(response.context['page'].next_page_number(), current_page + 1)

    def test_pagination_wrong_page_number(self):
        """Check that there's no page with page_number < 1 or page_number > max_page_number"""
        page_numbers = [-100, 0, 100]
        for current_page in page_numbers:
            c = Client()
            response = c.get(f'/?page={current_page}')

            self.assertEqual(response.status_code, 404)

    # TODO
    def test_pagination_invalid_page_number(self):
        """Check that page_number must be numeric value"""

class PostLikesTests(TestCase):
    def setUp(self):
        """Create some users and posts in db and like some posts"""
        # config db
        # db: create some users
        foo_credentials = { 'username': 'foo',  'password': 'foo' }
        bar_credentials = { 'username': 'bar',  'password': 'bar' }
        baz_credentials = { 'username': 'baz',  'password': 'baz' }

        foo = User.objects.create_user(**foo_credentials)
        bar = User.objects.create_user(**bar_credentials)
        baz = User.objects.create_user(**baz_credentials)

        # db: create some posts
        posts_to_add = [f'post #{i + 1}' for i in range(5)]
        for post_content in posts_to_add:
            Post.objects.create(content=post_content, user=bar)

        # db: add some likes
        post_to_like_and_unlike = Post.objects.first()
        baz.likes.add(post_to_like_and_unlike)

        # client/server config
        # instantiate
        self.client = Client()

        # client: identify resources
        self.post_to_like = post_to_like_and_unlike
        self.post_to_unlike = post_to_like_and_unlike

        id_of_post_that_exists = post_to_like_and_unlike.id
        id_of_post_that_doesnt_exist = Post.objects.all().aggregate(Max('id')).get('id__max') + 1

        self.id_of_post_to_like_that_exists = id_of_post_that_exists
        self.id_of_post_to_like_that_doesnt_exist = id_of_post_that_doesnt_exist

        self.id_of_post_to_unlike_that_exists = id_of_post_that_exists
        self.id_of_post_to_unlike_that_doesnt_exist = id_of_post_that_doesnt_exist

        # client: identify users
        self.user_who_already_liked_post = baz
        self.login_credentials_of_user_who_already_liked_post = baz_credentials

        self.user_who_hadnt_liked_post_yet = foo
        self.login_credentials_of_user_who_hadnt_liked_post_yet = foo_credentials

    def test_like_post_likes_count(self):
        """Check that when a user likes a post the post likes count increases"""
        self.user_who_hadnt_liked_post_yet.likes.add(self.post_to_like)
        self.assertEqual(self.user_who_hadnt_liked_post_yet.likes.count(), 1)
        self.assertEqual(self.post_to_like.fans.count(), 2) # baz, foo

    def test_unlike_post_likes_count(self):
        """Check that when a user unlikes a post (they already liked) the post likes count decreases"""
        self.user_who_already_liked_post.likes.remove(self.post_to_unlike)
        self.assertEqual(self.user_who_already_liked_post.likes.count(), 0)
        self.assertEqual(self.post_to_unlike.fans.count(), 0)

    def test_like_post_fails_notloggedin(self):
        """Check that liking a post fails if current user isn't logged-in"""
        response = self.client.post(f'/posts/{self.id_of_post_to_like_that_exists}/like')
        self.assertEqual(response.status_code, 401)

    def test_like_post_fails_notexist(self):
        """Check that liking a post fails if post doesn't exist in db"""
        # MUST LOGIN FIRST
        self.client.login(**self.login_credentials_of_user_who_hadnt_liked_post_yet)

        response = self.client.post(f'/posts/{self.id_of_post_to_like_that_doesnt_exist}/like')
        self.assertEqual(response.status_code, 404)

    def test_like_post_fails_alreadyliked(self):
        """Check that liking a post fails if current user already liked the post"""
        # MUST LOGIN FIRST
        self.client.login(**self.login_credentials_of_user_who_already_liked_post)

        response = self.client.post(f'/posts/{self.id_of_post_to_like_that_exists}/like')
        self.assertEqual(response.status_code, 400)

    def test_like_post_works(self):
        """Check that logged-in users can like (other users?) posts"""
        # MUST LOGIN FIRST
        self.client.login(**self.login_credentials_of_user_who_hadnt_liked_post_yet)

        response = self.client.post(f'/posts/{self.id_of_post_to_like_that_exists}/like', HTTP_REFERER='http://testserver/', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_unlike_post_fails_notloggedin(self):
        """Check that unliking a post fails if current user isn't logged-in"""
        response = self.client.post(f'/posts/{self.id_of_post_to_unlike_that_exists}/unlike')
        self.assertEqual(response.status_code, 401)

    def test_unlike_post_fails_notexist(self):
        """Check that unliking a post fails if post doesn't exist in db"""
        # MUST LOGIN FIRST
        self.client.login(**self.login_credentials_of_user_who_already_liked_post)

        response = self.client.post(f'/posts/{self.id_of_post_to_unlike_that_doesnt_exist}/unlike')
        self.assertEqual(response.status_code, 404)

    def test_unlike_post_fails_notlikedyet(self):
        """Check that unliking a post fails if current user hasn't liked the post yet"""
        # MUST LOGIN FIRST
        self.client.login(**self.login_credentials_of_user_who_hadnt_liked_post_yet)

        response = self.client.post(f'/posts/{self.id_of_post_to_unlike_that_exists}/unlike')
        self.assertEqual(response.status_code, 400)

    def test_unlike_post_works(self):
        """Check that logged-in users can unlike the posts they already liked"""
        # MUST LOGIN FIRST
        self.client.login(**self.login_credentials_of_user_who_already_liked_post)

        response = self.client.post(f'/posts/{self.id_of_post_to_unlike_that_exists}/unlike', HTTP_REFERER='http://testserver/', follow=True)
        self.assertEqual(response.status_code, 200)
