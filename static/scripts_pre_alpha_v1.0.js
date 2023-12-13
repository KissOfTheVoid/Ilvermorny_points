document.addEventListener('DOMContentLoaded', function() {
    loadFaculties();
    updateFacultyPoints();
});

function loadFaculties() {
    fetch('/faculties')
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
        })
        .catch(error => console.error('Ошибка:', error));
}

function updateFacultyPoints() {
    fetch('/get_faculty_points')
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

function changePoints(points) {
    const fullName = document.getElementById('wizard-name').value.trim();
    const facultyId = document.getElementById('faculty-select').value;
    const nameParts = fullName.split(' ');
    if (!fullName || nameParts.length !== 2) {
        alert('Пожалуйста, введите полное имя волшебника (имя и фамилия).');
        return;
    }
    const [senderName, senderSurname] = nameParts;

    const operation = points >= 0 ? 'add' : 'subtract';

    fetch('/points', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            faculty_id: facultyId,
            points: Math.abs(points),
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


function loadTransactions() {
    const name = document.getElementById('wizard-name').value;
    const surname = document.getElementById('wizard-surname').value;

    fetch(`/get_transactions_by_wizard?name=${name}&surname=${surname}`)
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
                row.insertCell(3).textContent = trans.sender_name + ' ' + trans.sender_surname;
            });
        })
        .catch(error => {
            console.error('Ошибка:', error);
            alert(error.message);  // Отображение сообщения об ошибке
        });
}


function exportTransactions() {
    const name = document.getElementById('wizard-name').value;
    const surname = document.getElementById('wizard-surname').value;

    if (!name || !surname) {
        alert('Пожалуйста, введите имя и фамилию волшебника.');
        return;
    }

    fetch(`/export_transactions?name=${name}&surname=${surname}`)
        .then(response => {
            if (response.ok) {
                return response.blob();
            } else {
                return response.json().then(json => {
                    throw new Error(json.message);
                });
            }
        })
        .then(blob => {
            // Создание ссылки для скачивания файла
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `transactions_${name}_${surname}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        })
        .catch(error => {
            alert(error.message); // Отображение сообщения об ошибке
        });
}

