// Событие, вызываемое после полной загрузки DOM
document.addEventListener('DOMContentLoaded', function() {
    loadFaculties(); // Загрузка списка факультетов
    updateFacultyPoints(); // Обновление баллов факультетов
    loadUsers(); // Загрузка пользователей

    // Добавляем обработчик для изменения выбранного факультета
    document.getElementById('faculty-select').addEventListener('change', function() {
        loadSelectedFacultyPoints(this.value); // Загрузка баллов выбранного факультета
    });
});

// Заголовки для всех запросов
const headers = {
    'Content-Type': 'application/json',
    'X-Custom-Security-Header': CUSTOM_HEADER_VALUE // Заголовок для безопасности
};

// Функция для загрузки списка факультетов
function loadFaculties() {
    fetch('/faculties', { headers: headers })
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('faculty-select');
            select.innerHTML = '';
            data.forEach(faculty => {
                const option = document.createElement('option');
                option.value = faculty.id;
                option.textContent = faculty.name;
                select.appendChild(option);
            });
            // Автоматическая загрузка данных для первого факультета
            if (data.length > 0) {
                select.value = data[0].id; // Устанавливаем первый факультет выбранным
                loadSelectedFacultyPoints(data[0].id); // Загрузка данных для первого факультета
            }
        })
        .catch(error => console.error('Ошибка:', error));
}

// Функция для обновления баллов факультетов
function updateFacultyPoints() {
    fetch('/get_faculty_points', { headers: headers })
        .then(response => response.json())
        .then(data => {
            const pointsContainer = document.getElementById('faculty-points-display');
            pointsContainer.innerHTML = '';
            Object.keys(data).forEach(facultyName => {
                const points = data[facultyName];
                const facultyContainer = document.createElement('div');
                facultyContainer.className = 'faculty-container';

                const facultyNameDiv = document.createElement('div');
                facultyNameDiv.className = 'faculty-name';
                facultyNameDiv.textContent = facultyName;

                const facultyPointsDiv = document.createElement('div');
                facultyPointsDiv.className = 'faculty-points';
                facultyPointsDiv.textContent = points;

                facultyContainer.appendChild(facultyNameDiv);
                facultyContainer.appendChild(facultyPointsDiv);
                pointsContainer.appendChild(facultyContainer);
            });
        })
        .catch(error => console.error('Error:', error));
}

// Функция для загрузки баллов выбранного факультета
function loadSelectedFacultyPoints(facultyId) {
    if (!facultyId) return; // Если ID факультета не выбран, ничего не делаем

    fetch(`/get_faculty_points_by_id/${facultyId}`, { headers: headers })
        .then(response => response.json())
        .then(data => {
            document.getElementById('faculty-name').textContent = data.name;
            document.getElementById('total-points').textContent = data.total_points;
            document.getElementById('courage-points').textContent = data.courage;
            document.getElementById('resourcefulness-points').textContent = data.resourcefulness;
            document.getElementById('kindness-points').textContent = data.kindness;
            document.getElementById('sports-points').textContent = data.sports;
        })
        .catch(error => console.error('Ошибка:', error));
}
// Функция для изменения баллов
function changePoints(points) {
    const fullName = document.getElementById('wizard-name').value.trim();
    const facultyId = document.getElementById('faculty-select').value;
    const nameParts = fullName.split(' ');
    const pointsType = document.getElementById('points-type-select').value;

    if (!fullName || nameParts.length !== 2) {
        alert('Пожалуйста, введите полное имя волшебника (имя и фамилия).');
        return;
    }

    const [senderName, senderSurname] = nameParts;
    const operation = points >= 0 ? 'add' : 'subtract';

    fetch('/points', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
            faculty_id: facultyId,
            points: Math.abs(points),
            points_type: pointsType,
            sender_name: senderName,
            sender_surname: senderSurname,
            operation: operation
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Баллы успешно изменены.');
            updateFacultyPoints(); // Обновление баллов факультетов после изменения
        } else {
            alert('Произошла ошибка при изменении баллов.');
        }
    })
    .catch(error => console.error('Ошибка:', error));
}

// Функция для загрузки транзакций
function loadTransactions() {
    const selectedWizard = document.getElementById('wizard-select').value;
    const [name, surname] = selectedWizard.split(' ');

    if (!selectedWizard || name.length === 0 || surname.length === 0) {
        alert('Пожалуйста, выберите волшебника из списка.');
        return;
    }

    fetch(`/get_transactions_by_wizard?name=${encodeURIComponent(name)}&surname=${encodeURIComponent(surname)}`, { headers: headers })
        .then(response => {
            if (!response.ok) {
                throw new Error('Волшебник не найден');
            }
            return response.json();
        })
        .then(data => {
            const logTableBody = document.getElementById('transactions-log').getElementsByTagName('tbody')[0];
            logTableBody.innerHTML = '';

            data.forEach(trans => {
                let row = logTableBody.insertRow();
                row.insertCell(0).textContent = trans.timestamp;
                row.insertCell(1).textContent = trans.faculty_name;
                row.insertCell(2).textContent = trans.points;
                row.insertCell(3).textContent = translatePointsType(trans.points_type);
                row.insertCell(4).textContent = trans.sender_name + ' ' + trans.sender_surname;
            });
        })
        .catch(error => {
            console.error('Ошибка:', error);
            alert(error.message);
        });
}

// Функция для перевода типа баллов
function translatePointsType(type) {
    const types = {
        'courage': 'Смелость',
        'resourcefulness': 'Находчивость',
        'kindness': 'Доброта',
        'sports': 'Спорт'
    };
    return types[type] || type; // Возвращает перевод или оригинальное значение, если перевода нет
}

// Функция для экспорта транзакций
function exportTransactions() {
    const selectedWizard = document.getElementById('wizard-select').value;
    const [name, surname] = selectedWizard.split(' ');

    if (!selectedWizard || name.length === 0 || surname.length === 0) {
        alert('Пожалуйста, выберите волшебника из списка.');
        return;
    }

    fetch(`/export_transactions?name=${encodeURIComponent(name)}&surname=${encodeURIComponent(surname)}`, { headers: headers })
        .then(response => {
            if (!response.ok) {
                return response.json().then(json => {
                    throw new Error(json.message);
                });
            }
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `transactions_${name}_${surname}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        })
        .catch(error => {
            alert(error.message);
        });
}

// Функция для загрузки пользователей
function loadUsers() {
    fetch('/get_users', { headers: headers })
        .then(response => response.json())
        .then(users => {
            const select = document.getElementById('wizard-select');
            select.innerHTML = '<option value="">--Выберите волшебника--</option>';
            users.forEach(user => {
                const option = document.createElement('option');
                option.value = `${user[0]} ${user[1]}`;
                option.text = `${user[0]} ${user[1]}`;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Ошибка при загрузке пользователей:', error));
}
