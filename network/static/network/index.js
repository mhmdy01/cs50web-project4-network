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
});
