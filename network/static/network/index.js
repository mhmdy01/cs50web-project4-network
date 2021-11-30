// ====== dom helper functions ====== //

// check if clicked element is like-post btn
function isLikeBtn(elm) {
    return elm && (elm.matches('.like-post') || elm.parentElement.matches('.like-post'));
}

// check if clicked element is unlike-post btn
function isUnlikeBtn(elm) {
    return elm && (elm.matches('.unlike-post') || elm.parentElement.matches('.unlike-post'));
}

// check if clicked element is edit-post btn
// that is used to show post editing view
function isEditBtn(elm) {
    return elm && elm.matches('.edit-post');
}

// check if clicked element is cancel-edit-post btn
// that is used to return to post content view
function isCancelEditBtn(elm) {
    return elm && elm.matches('.cancel-edit-post');
}

// check if clicked element is save-edit-post btn
// that is used to send edits/changes to server
// and return to post content view
function isSaveEditBtn(elm) {
    return elm && elm.matches('.save-edit-post');
}

// ====== dom manipulation functions ====== //

// when showing post editing view
// textarea element must be pre-populated with current post content
function prepopulateTextArea(postContentView, postContentEditingView) {
    const currentContent = postContentView.querySelector('p').innerHTML;
    postContentEditingView.querySelector('textarea').value = currentContent;
}

// show post editing form when user clicks edit button
function showEditPostForm(postContentView, postContentEditingView) {
    // first: hide post content view
    postContentView.style.display = 'none';

    // then: show post editing view
    postContentEditingView.style.display = 'block';

    prepopulateTextArea(postContentView, postContentEditingView);
}

// hide post editing form if user decides to cancel their edits
// or after saving their changes by submitting them to server
function hideEditPostForm(postContentView, postContentEditingView) {
    // first: hide post editing view
    postContentEditingView.style.display = 'none';

    // then: show post content view
    postContentView.style.display = 'block';
}

// replace post content with updated content (from server response)
function updatePostContent(postContentView, updatedContent) {
    postContentView.querySelector('p').innerHTML = updatedContent;
}

// replace post likes with updated likes (from server response)
function updatePostLikes(postId, updatedLikes) {
    const postDiv = document.querySelector(`div[data-id="${postId}"]`)
    const likesDiv = postDiv.querySelector('div.likes-container')
    likesDiv.innerHTML = updatedLikes;
}

// ====== http helper functions ====== //

// send an http request
async function sendRequest(url, method='GET', headers={}, body=null) {
    const reqHeaders = new Headers(headers)
    const reqConfig = {
        method: method,
        headers: reqHeaders,
        body: body
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
    // response body could be json or not json
    // not json will mainly be plaintext or html
    // nothing more to expect
    // because we control response content-type at server!
    if (res.headers.get('content-type').match(/json/i)) {
        var resBody = await res.json();
    } else {
        var resBody = await res.text();
    }
    if (res.ok) {
        return resBody;
    } else {
        throw new Error(resBody);
    }
}

// ====== ajax functions ====== //

// when user save their edits
// send a put request to server to update post content
async function updatePost(postId, postContentView, postContentEditingView) {
    // get changed content
    const newContent = postContentEditingView.querySelector('textarea').value;

    // send the request
    // TODO: add validation and error handling here
    // also, MUST DISPLAY A NOTIFICATION for user detailing
    // server response/reason for rejecting the request
    try {
        const resBody = await sendRequest(`posts/${postId}/edit`, 'PUT', {}, JSON.stringify({ content: newContent }));
        updatePostContent(postContentView, resBody);
        hideEditPostForm(postContentView, postContentEditingView);
    } catch (error) {
        console.log(`update_post | ERROR |`, error.message);
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
    document.querySelectorAll('.post').forEach(postDiv => {
        const postId = postDiv.dataset.id;
        // post content container div has two views
        // content view: which include the actual content
        // content editing view: which include the editing form
        const postContentDiv = postDiv.querySelector('.content-container');
        const [postContentEditingView, postContentView] = Array.from(postContentDiv.children);
        const postEditingForm = postContentEditingView.querySelector('form');

        // editing view should be initially hidden
        postContentEditingView.style.display = 'none';

        // attach an event handler for clicks at post div
        // then check for the actual elm -inside post div- that triggered the click
        // and perform the required/correct operation related to that elm
        // this is done according to (event delegation) technique
        // check: https://davidwalsh.name/event-delegate
        postDiv.onclick = (event) => {
            // const postDiv = event.currentTarget;
            const clickedElement = event.target;

            if (isLikeBtn(clickedElement)) {
                likePost(postId);
            } else if (isUnlikeBtn(clickedElement)) {
                unLikePost(postId);
            } else if (isEditBtn(clickedElement)) {
                showEditPostForm(postContentView, postContentEditingView);
            } else if (isCancelEditBtn(clickedElement)) {
                hideEditPostForm(postContentView, postContentEditingView);
            }
        }

        // handle editing form submission
        postEditingForm.onsubmit = () => {
            updatePost(postId, postContentView, postContentEditingView);

            // disable default form submission behavior
            return false;
        }
    })
});
