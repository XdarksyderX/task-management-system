document.addEventListener('DOMContentLoaded', function () {
    const commentList = document.getElementById('comment-list');
    const commentForm = document.getElementById('comment-form');
    const commentInput = document.getElementById('comment-input');

    // The taskId and requestUser are expected to be defined in the HTML template
    if (typeof taskId === 'undefined' || typeof requestUser === 'undefined') {
        console.error('Required variables (taskId, requestUser) are not defined.');
        return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8002/ws/tasks/${taskId}/comments/`;
    const commentSocket = new WebSocket(wsUrl);

    commentSocket.onopen = function(e) {
        console.log('Comment WebSocket connection established.');
        // Request existing comments upon connection
        commentSocket.send(JSON.stringify({
            'type': 'comment.fetch'
        }));
    };

    commentSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        
        switch (data.type) {
            case 'comment.history':
                // Clear existing comments and load history
                commentList.innerHTML = '';
                data.comments.forEach(comment => {
                    appendComment(comment);
                });
                break;
            case 'comment.added':
                // Append a new comment
                appendComment(data.comment);
                break;
            case 'comment.edited':
                // Update an existing comment
                updateComment(data.comment);
                break;
            case 'comment.deleted':
                // Remove a deleted comment
                removeComment(data.comment_id);
                break;
            case 'comment.error':
                alert(`Error: ${data.message}`);
                break;
            default:
                console.warn('Unknown message type:', data.type);
        }
    };

    commentSocket.onclose = function(e) {
        console.error('Comment WebSocket connection closed unexpectedly.');
    };

    commentSocket.onerror = function(err) {
        console.error('WebSocket error:', err);
    };

    commentForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const message = commentInput.value.trim();

        if (message) {
            commentSocket.send(JSON.stringify({
                'type': 'comment.add',
                'content': message
            }));
            commentInput.value = '';
        }
    });

    function appendComment(comment) {
        const commentItem = document.createElement('div');
        commentItem.className = 'comment-item';
        commentItem.dataset.commentId = comment.id;

        const authorName = comment.author_name || 'Anonymous';
        const createdDate = new Date(comment.created_at).toLocaleString();
        const isOwnComment = requestUser && comment.author && comment.author.id === requestUser.id;

        commentItem.innerHTML = `
            <div class="comment-meta">
                <strong>${authorName}</strong>
                <span>- ${createdDate}</span>
                ${isOwnComment ? `
                    <div class="comment-actions">
                        <button onclick="editComment(${comment.id})" class="btn-edit">Edit</button>
                        <button onclick="deleteComment(${comment.id})" class="btn-delete">Delete</button>
                    </div>
                ` : ''}
            </div>
            <div class="comment-content">
                <p>${comment.content}</p>
            </div>
        `;
        
        commentList.appendChild(commentItem);
        // Scroll to the bottom of the comment list
        commentList.scrollTop = commentList.scrollHeight;
    }

    function updateComment(comment) {
        const commentItem = commentList.querySelector(`[data-comment-id="${comment.id}"]`);
        if (commentItem) {
            const contentElement = commentItem.querySelector('.comment-content p');
            if (contentElement) {
                contentElement.textContent = comment.content;
            }
        }
    }

    function removeComment(commentId) {
        const commentItem = commentList.querySelector(`[data-comment-id="${commentId}"]`);
        if (commentItem) {
            commentItem.remove();
        }
    }

    // Global functions for comment actions
    window.editComment = function(commentId) {
        const commentItem = commentList.querySelector(`[data-comment-id="${commentId}"]`);
        if (commentItem) {
            const contentElement = commentItem.querySelector('.comment-content p');
            const currentContent = contentElement.textContent;
            
            const newContent = prompt('Edit comment:', currentContent);
            if (newContent && newContent.trim() !== currentContent) {
                commentSocket.send(JSON.stringify({
                    'type': 'comment.edit',
                    'comment_id': commentId,
                    'content': newContent.trim()
                }));
            }
        }
    };

    window.deleteComment = function(commentId) {
        if (confirm('Are you sure you want to delete this comment?')) {
            commentSocket.send(JSON.stringify({
                'type': 'comment.delete',
                'comment_id': commentId
            }));
        }
    };
});
