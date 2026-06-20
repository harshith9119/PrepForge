readme_content = """# 🚀 PrepForge: The Ultimate Placement Preparation Platform

PrepForge is a professional-grade, full-stack web application designed to help engineering students master Data Structures and Algorithms (DSA) for technical interviews. It features a curated roadmap of 500+ high-frequency interview questions, progress tracking, and a secure admin management system.

## 🌟 Key Features

* **Comprehensive DSA Roadmap:** A structured curriculum covering 10 major topics (Basics, Recursion, Array, Binary Search, Linked List, Stack, Queue, Tree, Graph, and DP).
* **Progress Tracking:** Users can track their problem-solving journey, mark problems as solved, and monitor their progress.
* **Secure Authentication:** Full user registration and login system with password hashing (`werkzeug.security`) and session management.
* **Admin Dashboard:** A robust admin panel to manage, add, edit, and delete problems.
* **Bulk Management:** Efficient CSV bulk-upload functionality to import hundreds of problems in seconds.
* **Responsive UI:** Modern, mobile-responsive design built with **Tailwind CSS**.

## 🛠 Tech Stack

* **Backend:** Python (Flask)
* **Database:** SQLite (Relational Schema)
* **Frontend:** HTML5, Jinja2 Templates, Tailwind CSS
* **Tools:** AJAX for asynchronous data updates, CSV processing via Python `csv` & `io` modules.

## 🏗 Architecture Overview

```text
[ Browser ] <---> [ Flask Web Server ] <---> [ SQLite Database ]
                         |
                 [ Admin Utilities ]
                         |
                 [ Bulk Upload Script ]




## 🔮 Future Roadmap: Smart AI Mentorship

The next milestone for PrepForge is shifting it from a progress tracker into an active AI-driven study mentor:

* **Retrieval-Augmented Generation (RAG) Integration:** Building a custom RAG architecture using Python to index problem descriptions, constraints, and algorithmic patterns.
* **Contextual Problem-Solving Agent:** Implementing an interactive assistant that pulls data directly from the SQLite database to guide users with smart hints, code complexity analysis (Time/Space complexities), and edge-case warnings without directly giving away the final answer.
