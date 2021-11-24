function syncTextAreaElementWithCurrentContent(editPostFormDiv) {
    const currentContent = editPostFormDiv.nextElementSibling.querySelector('p').innerHTML;
    editPostFormDiv.querySelector('textarea').value = currentContent;
}

function showEditPostForm(postContentDiv) {
    // hide post
    postContentDiv.style.display = 'none';

    // show edit post form
    const editPostFormDiv = postContentDiv.previousElementSibling;
    editPostFormDiv.style.display = 'block';

    // pre-populate textarea element with current content
    syncTextAreaElementWithCurrentContent(editPostFormDiv);
}

function hideEditPostForm(editPostFormDiv) {
    // hide edit post form
    editPostFormDiv.style.display = 'none';

    // also must reset any changes user has made
    syncTextAreaElementWithCurrentContent(editPostFormDiv);

    // show post
    const postContentDIv = editPostFormDiv.nextElementSibling;
    postContentDIv.style.display = 'block';
}

function updatePost(event) {
    const editPostForm = event.target;
    const editPostFormDiv = editPostForm.parentElement;

    // get updated content
    const newContent = editPostForm.querySelector('textarea').value;

    // TODO: add validation and error handling here
    // RECALL: fetch ONLY rejects (@network errors) NOT (http responses)
    // so you need to manually handle this. (eg. raise or throw some exception)
    // also, MUST DISPLAY A NOTIFICATION for user detailing
    // server response/reason for rejecting the request
    // send a put request to server to update post content
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    fetch(editPostForm.action, {
        method: 'PUT',
        headers: {'X-CSRFToken': csrftoken},
        body: JSON.stringify({ content: newContent })
    })
        .then(res => res.json())
        .then(data => {
            // replace post current content with updated content
            editPostFormDiv.nextElementSibling.querySelector('p').innerHTML = data.content;
            
            // hide edit post form and show post
            hideEditPostForm(editPostFormDiv);
            
            // also, replace textarea content with updated content
            // i think no need for this?
            // syncTextAreaElementWithCurrentContent(editPostFormDiv);
        })
        .catch(error => {
            console.log(error);
        })
    return false;
}

// check if clicked element is like-post btn
function isLikeBtn(elm) {
    return elm && (elm.matches('.like-post') || elm.parentElement.matches('.like-post'));
}

// check if clicked element is unlike-post btn
function isUnlikeBtn(elm) {
    return elm && (elm.matches('.unlike-post') || elm.parentElement.matches('.unlike-post'));
}

// replace post likes with updated likes (from server response)
function updatePostLikes(postId, updatedLikes) {
    const postDiv = document.querySelector(`div[data-id="${postId}"]`)
    const likesDiv = postDiv.querySelector('div.likes-container')
    likesDiv.innerHTML = updatedLikes;
}

// send an http request
async function sendRequest(url, method='GET', headers={}, body=null) {
    const reqHeaders = new Headers(headers)
    const reqConfig = {
        method: method,
        headers: reqHeaders
    }
    if (reqConfig.method == 'POST' || reqConfig.method == 'PUT') {
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        reqConfig.headers.append('X-CSRFToken', csrftoken);
    }
    const req = new Request(url, reqConfig);

    // send req and handle network errors
    // eg. couldn't send request (no internet)
    let res;
    try {
        res = await fetch(req);
    } catch (error) {
        console.log(error);
    }

    // get response body and handle server errors
    // eg. unauthorized action
    // this is done manually and separately from fetch error handling
    // as fetch ONLY REJECT @network errors NOT http status codes
    // eg. responses with status code != 200
    // check: https://www.tjvantoll.com/2015/09/13/fetch-and-errors/
    const resBody = await res.text();
    if (res.ok) {
        return resBody;
    } else {
        throw new Error(resBody);
    }
}

// like post when user clicks like btn
async function likePost(postId) {
    // console.log(`liking post#${postId}`);
    try {
        const resBody = await sendRequest(`/posts/${postId}/like`, 'POST');
        updatePostLikes(postId, resBody);
    } catch (error) {
        console.log('like_post', '|', error.message);
    }
}

// unlike post when user clicks unlike btn
async function unLikePost(postId) {
    // console.log(`unliking post#${postId}`);
    try {
        const resBody = await sendRequest(`/posts/${postId}/unlike`, 'POST');
        updatePostLikes(postId, resBody);
    } catch (error) {
        console.log('unlike_post', '|', error.message);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // show form for editing post when user clicks edit button
    document.querySelectorAll('.edit-post').forEach(btn => {
        btn.onclick = () => {
            showEditPostForm(btn.parentElement);
        }
    })

    // hide edit post form if user decides to cancel their edits
    document.querySelectorAll('.cancel-edit-post').forEach(btn => {
        btn.onclick = () => {
            hideEditPostForm(btn.parentElement.parentElement);
        }
    })

    // handle edit post form submission
    document.querySelectorAll('.edit-post-form').forEach(form => {
        form.onsubmit = updatePost;
    })

    document.querySelectorAll('.post').forEach(post => {
        // attach an event handler for clicks at post div
        // then check for the actual elm -inside post div- that triggered the click
        // and perform the required/correct operation related to that elm
        // this is done according to (event delegation) technique
        // check: https://davidwalsh.name/event-delegate
        post.onclick = (event) => {
            const postDiv = event.currentTarget;
            const clickedElement = event.target;

            if (isLikeBtn(clickedElement)) {
                likePost(postDiv.dataset.id);
            } else if (isUnlikeBtn(clickedElement)) {
                unLikePost(postDiv.dataset.id);
            }
        }
    })
});
