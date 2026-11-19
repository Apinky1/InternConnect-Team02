
# InternConnect — Team02

**Winston-Salem State University | Software Engineering Group Project**

InternConnect is a cloud-based internship and career-readiness web application designed to help students organize internship applications, monitor deadlines, prepare for interviews, and track their career development.

## Live Application

https://internconnect-team02.onrender.com/

## GitHub Repository

https://github.com/Apinky1/InternConnect-Team02

## Core Features

1. **Application Management:** Add, edit, view, and delete internship applications, including company, position, and deadline information.
2. **Application Status Tracking:** Update application statuses and view summary counts on the dashboard.
3. **Interview and Deadline Management:** Schedule, view, and delete interviews and important deadlines associated with applications.
4. **Career Readiness Checklist:** Track career preparation tasks, mark items complete, add custom tasks, and monitor progress.
5. **Career Dashboard:** View application statistics, checklist progress, and upcoming interviews and deadlines.

## Technologies Used

- Frontend: HTML, CSS, JavaScript, and Jinja2 templates
- Backend: Python and Flask
- Database: SQLite
- Version Control: Git and GitHub
- Containerization: Docker
- Cloud Deployment: Render
- Testing: pytest

## Run Locally (Windows PowerShell)

Clone or download the GitHub repository and open its folder in a terminal.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000 in your browser.

If the `py` command is unavailable, use `python -m venv .venv` to create the virtual environment.

## Run Automated Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The integrated application passed all 62 automated tests during final local verification.

## Docker

The repository includes a Dockerfile for containerization.

Build the image:

```powershell
docker build -t internconnect .
```

Run the container:

```powershell
docker run --rm -p 5000:5000 internconnect
```

Open http://127.0.0.1:5000 to access the containerized application.

## Team Contributions

**Aliyah — Project Coordinator and Frontend Developer**
- Designed and implemented the user interface and dashboard styling.
- Integrated frontend templates with the Flask backend.
- Developed navigation and improved the user experience.
- Conducted manual functionality and interface testing.
- Coordinated project progress and GitHub contributions.

**Makeda — Backend and Database Developer**
- Implemented Flask routes, application management, and validation.
- Developed SQLite database functionality for applications, events, and checklist tasks.
- Implemented dashboard data integration and error handling.
- Developed and executed automated tests.
- Supported backend integration and verification.

**Taylor — Product Planning, Documentation, Presentation, and Deployment**
- Contributed product vision, user stories, and project planning documentation.
- Prepared presentation and project documentation.
- Coordinated the Render cloud deployment.

All members collaborated on project development, communication, testing, and final delivery.

## Testing and Quality Assurance

The team tested major user workflows, including application creation, editing, status updates, and deletion; interview and deadline management; checklist progress tracking; and dashboard functionality.

The project includes automated tests for Flask routes, input validation, error handling, and database operations.

## Current Limitations

InternConnect is an academic project and does not include individual user accounts or authentication. The deployed demo should not be used to store sensitive personal information.

The application uses SQLite. Database persistence depends on the deployment environment and configured storage. Render deployments without persistent storage may lose application data during restarts or redeployments.

## Project Documentation

Additional project planning and supporting documentation are located in the `docs` folder.

This application was developed as a collaborative Software Engineering project at Winston-Salem State University.
