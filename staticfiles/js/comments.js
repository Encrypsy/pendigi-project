function initCommentSection() {
    const root = document.getElementById('commentsRoot');
    if (!root) return;

    root.addEventListener('submit', function (e) {
        const form = e.target.closest('form');
        if (!form) return;
        e.preventDefault();

        fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(res => res.json())
        .then(data => {
            if (data.ok) {
                refreshComments();
            } else if (data.error) {
                alert(data.error);
            }
        })
        .catch(() => alert('Terjadi kesalahan, coba lagi.'));
    });

    const sortSelect = root.querySelector('.sort-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', function () {
            refreshComments(this.value);
        });
    }
}

function refreshComments(sortOverride) {
    const root = document.getElementById('commentsRoot');
    const sort = sortOverride || root.dataset.currentSort;
    const url = root.dataset.refreshUrl + '?sort=' + sort;

    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(res => res.text())
        .then(html => {
            root.outerHTML = html;
            initCommentSection();
        });
}

function toggleReplyForm(id) {
    const f = document.getElementById('reply-form-' + id);
    f.style.display = f.style.display === 'none' ? 'flex' : 'none';
}
function toggleReplies(id) {
    const list = document.getElementById('replies-' + id);
    const label = document.getElementById('toggle-label-' + id);
    const hidden = list.style.display === 'none';
    if (hidden && !label.dataset.original) label.dataset.original = label.textContent;
    list.style.display = hidden ? 'block' : 'none';
    label.textContent = hidden ? 'Sembunyikan balasan' : label.dataset.original;
}
function toggleOptions(id) {
    document.querySelectorAll('.comment-options-menu.is-open').forEach(m => { if (m.id !== 'options-' + id) m.classList.remove('is-open'); });
    document.getElementById('options-' + id).classList.toggle('is-open');
}
function startEdit(id) {
    document.getElementById('text-' + id).style.display = 'none';
    document.getElementById('edit-form-' + id).style.display = 'block';
    document.getElementById('options-' + id).classList.remove('is-open');
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('.comment-options-wrap')) {
        document.querySelectorAll('.comment-options-menu.is-open').forEach(m => m.classList.remove('is-open'));
    }
});

document.addEventListener('DOMContentLoaded', initCommentSection);