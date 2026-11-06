
function toggleReplyForm(id) {
    const form = document.getElementById('reply-form-' + id);

    if (!form) return;

    form.style.display =
        form.style.display === 'none' ? 'flex' : 'none';
}

function toggleReplies(id) {
    const list = document.getElementById('replies-' + id);
    const label = document.getElementById('toggle-label-' + id);

    if (!list || !label) return;

    const hidden = list.style.display === 'none';

    if (hidden && !label.dataset.original) {
        label.dataset.original = label.textContent;
    }

    list.style.display = hidden ? 'block' : 'none';

    label.textContent = hidden
        ? 'Sembunyikan balasan'
        : label.dataset.original;
}

function toggleOptions(id) {
    document.querySelectorAll(
        '.comment-options-menu.is-open'
    ).forEach(menu => {
        if (menu.id !== 'options-' + id) {
            menu.classList.remove('is-open');
        }
    });

    const menu = document.getElementById('options-' + id);

    if (menu) {
        menu.classList.toggle('is-open');
    }
}

function startEdit(id) {
    const text = document.getElementById('text-' + id);
    const form = document.getElementById('edit-form-' + id);
    const options = document.getElementById('options-' + id);

    if (text) text.style.display = 'none';
    if (form) form.style.display = 'block';
    if (options) options.classList.remove('is-open');
}

document.addEventListener('click', (event) => {
    if (!event.target.closest('.comment-options-wrap')) {
        document.querySelectorAll(
            '.comment-options-menu.is-open'
        ).forEach(menu => {
            menu.classList.remove('is-open');
        });
    }
});
