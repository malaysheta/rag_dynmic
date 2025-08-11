document.getElementById('uploadBtn').addEventListener('click', async () => {
    const pdfInput = document.getElementById('pdfInput');
    const uploadStatus = document.getElementById('uploadStatus');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileSelect = document.getElementById('fileSelect');
    const queryBtn = document.getElementById('queryBtn');

    if (!pdfInput.files.length) {
        uploadStatus.textContent = 'Please select a PDF file.';
        return;
    }

    uploadBtn.disabled = true;
    uploadStatus.textContent = 'Uploading...';

    const formData = new FormData();
    formData.append('file', pdfInput.files[0]);

    try {
        const response = await fetch('http://localhost:8000/upload_pdf/', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (response.ok) {
            uploadStatus.textContent = result.message;
            uploadStatus.classList.add('text-green-600');
            // Update file selection
            updateFileList(result.files);
            queryBtn.disabled = false; // Enable query button after first upload
        } else {
            uploadStatus.textContent = result.detail || 'Upload failed.';
            uploadStatus.classList.add('text-red-600');
        }
    } catch (error) {
        uploadStatus.textContent = 'Error uploading PDF.';
        uploadStatus.classList.add('text-red-600');
    } finally {
        uploadBtn.disabled = false;
    }
});

document.getElementById('removeFileBtn').addEventListener('click', async () => {
    const fileSelect = document.getElementById('fileSelect');
    const removeFileBtn = document.getElementById('removeFileBtn');
    const selectedFile = fileSelect.value;

    if (!selectedFile) {
        alert('Please select a file to remove.');
        return;
    }

    removeFileBtn.disabled = true;

    try {
        const response = await fetch('http://localhost:8000/remove_file/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_name: selectedFile })
        });
        const result = await response.json();

        if (response.ok) {
            updateFileList(result.files);
            alert(result.message);
        } else {
            alert(result.detail || 'Removal failed.');
        }
    } catch (error) {
        alert('Error removing file.');
    } finally {
        removeFileBtn.disabled = false;
    }
});

document.getElementById('queryBtn').addEventListener('click', async () => {
    const queryInput = document.getElementById('queryInput');
    const responseOutput = document.getElementById('responseOutput');
    const queryBtn = document.getElementById('queryBtn');
    const fileSelect = document.getElementById('fileSelect');

    if (!queryInput.value.trim()) {
        responseOutput.innerHTML = '<p class="text-sm text-red-500">Please enter a question.</p>';
        return;
    }

    if (!fileSelect.value) {
        responseOutput.innerHTML = '<p class="text-sm text-red-500">Please select a PDF file.</p>';
        return;
    }

    queryBtn.disabled = true;
    responseOutput.innerHTML = '<p class="text-sm text-gray-500">Processing...</p>';

    try {
        const response = await fetch('http://localhost:8000/query/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: queryInput.value })
        });
        const result = await response.json();

        if (response.ok) {
            responseOutput.innerHTML = `<p class="text-sm text-gray-800">${result.response.replace(/\n/g, '<br>')}</p>`;
        } else {
            responseOutput.innerHTML = `<p class="text-sm text-red-500">${result.detail || 'Query failed.'}</p>`;
        }
    } catch (error) {
        responseOutput.innerHTML = '<p class="text-sm text-red-500">Error processing query.</p>';
    } finally {
        queryBtn.disabled = false;
        queryInput.value = '';
    }
});

// Function to update file list in dropdown
async function updateFileList(files) {
    const fileSelect = document.getElementById('fileSelect');
    const removeFileBtn = document.getElementById('removeFileBtn');
    fileSelect.innerHTML = '<option value="">-- Select a file --</option>';
    files.forEach(file => {
        const option = document.createElement('option');
        option.value = file;
        option.textContent = file;
        fileSelect.appendChild(option);
    });
    removeFileBtn.disabled = files.length === 0;
}

// Initial load of uploaded files
window.addEventListener('load', async () => {
    try {
        const response = await fetch('http://localhost:8000/get_uploaded_files/');
        const result = await response.json();
        if (response.ok) {
            updateFileList(result.files);
        }
    } catch (error) {
        console.error('Error loading files:', error);
    }
});