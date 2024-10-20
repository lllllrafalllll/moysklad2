document.getElementById('addItemForm').addEventListener('submit', async function(event) {
    event.preventDefault();
    const skus = document.getElementById('skus').value;
    const response = await fetch(`/document/${doc_id}/add_item`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            'skus': skus
        })
    });

    const errorMessageElement = document.getElementById('error-message');

    if (response.ok) {
        // Очистить сообщение об ошибке, если товар добавлен успешно
        errorMessageElement.style.display = 'none';
        errorMessageElement.textContent = '';

        // Перезагрузить страницу или обновить список товаров (в зависимости от вашей логики)
        location.reload();
    } else {
        const data = await response.json();
        // Показать сообщение об ошибке
        errorMessageElement.style.display = 'block';
        errorMessageElement.textContent = data.error || "Ошибка при добавлении товара";
    }
});


document.querySelector('.save-document-form form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const formData = new FormData(this);
    const response = await fetch('/save_document', {
        method: 'POST',
        body: formData
    });

    const errorMessageElement = document.getElementById('error-message');

    const data = await response.json();

    if (response.ok) {
        // Если есть поле redirect, перенаправляем пользователя
        if (data.redirect) {
            window.location.href = data.redirect;
        }
    } else {
        // Показать сообщение об ошибке
        errorMessageElement.style.display = 'block';
        errorMessageElement.textContent = data.error || "Ошибка при сохранении документа";
    }
});
