from django.core.paginator import Paginator, InvalidPage


def get_page(posts, page_number):
    # show 10 posts per page
    paginator = Paginator(posts, 10)
    try:
        page = paginator.page(page_number)
    # handle wrong page number: page_num < 1, page_num > max_page_num
    except InvalidPage:
        page = None
    return page
