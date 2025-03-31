from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import zipfile
import os
from fpdf import FPDF

app = Flask(__name__, template_folder="../templates", static_folder="../static")  # Set correct template path)
app.secret_key = 'your_secret_key'  # Needed for flashing messages

# Function to calculate grades and remarks
def calculate_grade(marks):
    if marks < 50:
        return 'D', 'FAIL'
    elif 50 <= marks <= 64:
        return 'C', 'PASS'
    elif 65 <= marks <= 74:
        return 'B', 'CREDIT'
    else:
        return 'A', 'DISTINCTION'

# Ensure temp folder exists
TEMP_FOLDER = "temp_transcripts"
os.makedirs(TEMP_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            # Get common details (same for all students)
            school_name = request.form.get('school_name', 'Unknown School')
            semester = request.form.get('semester', 'Unknown Semester')
            class_name = request.form.get('class_name', 'Unknown Class')
            remarks = request.form.get('remarks', 'No remarks provided')
            coordinator_name = request.form.get('coordinator_name', 'N/A')
            coordinator_sign = request.form.get('coordinator_sign', 'N/A')
            coordinator_date = request.form.get('coordinator_date', 'N/A')
            hod_name = request.form.get('hod_name', 'N/A')
            hod_sign = request.form.get('hod_sign', 'N/A')
            hod_date = request.form.get('hod_date', 'N/A')

            # Get subject codes and names
            subject_codes = request.form.getlist('subject_code[]')
            subjects = request.form.getlist('subject[]')

            # Get student details
            student_names = request.form.getlist('student_name[]')
            reg_nos = request.form.getlist('reg_no[]')

            # Get marks and handle errors
            marks_list = []
            for i in range(len(student_names)):
                raw_marks = request.form.getlist(f'marks_{i}[]')
                marks = []
                for mark in raw_marks:
                    try:
                        marks.append(int(mark.replace(',', '').strip()))  # Remove commas before conversion
                    except ValueError:
                        flash(f"Invalid mark '{mark}' for student {student_names[i]}. Skipping this entry.")
                        marks.append(0)  # Default to 0 if conversion fails
                marks_list.append(marks)

            # Generate transcripts for each student
            transcript_files = []
            for i in range(len(student_names)):
                student_name = student_names[i]
                reg_no = reg_nos[i]
                marks = marks_list[i]

                total_marks = sum(marks)
                average_marks = round(total_marks / len(marks), 2)
                results = [(subject_codes[j], subjects[j], marks[j], *calculate_grade(marks[j])) for j in range(len(subjects))]

                # Generate PDF Transcript
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font('Arial', 'B', 12)

                # Add school logo (ensure file exists)
                logo_path = 'school_logo.jpg'  # Update with correct path
                if os.path.exists(logo_path):
                    page_width = pdf.w
                    logo_width = 50  # Adjust based on logo size
                    logo_height = 30  # Adjust as needed

                    # Center the logo at the top
                    logo_x = (page_width - logo_width) / 2  # Center horizontally
                    logo_y = 10  # Position at the top

                    pdf.image(logo_path, x=logo_x, y=logo_y, w=logo_width, h=logo_height)

                # Add School Name Below the Logo
                pdf.ln(logo_height + 5)  # Move down after logo
                pdf.cell(200, 10, school_name, ln=True, align='C')
                pdf.cell(200, 10, f"Student Transcript - {semester}", ln=True, align='C')
                pdf.cell(200, 10, f"Name: {student_name}             Reg No: {reg_no}        Class: {class_name}", ln=True, align='C')
                pdf.ln(10)

                # Table headers
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(30, 10, 'Code', 1)
                pdf.cell(60, 10, 'Subject', 1)
                pdf.cell(30, 10, 'Marks', 1)
                pdf.cell(30, 10, 'Grade', 1)
                pdf.cell(40, 10, 'Remarks', 1)
                pdf.ln()

                # Table content
                pdf.set_font('Arial', '', 10)
                for code, subj, mark, grade, remark in results:
                    pdf.cell(30, 10, code, 1)
                    pdf.cell(60, 10, subj, 1)
                    pdf.cell(30, 10, str(mark), 1)
                    pdf.cell(30, 10, grade, 1)
                    pdf.cell(40, 10, remark, 1)
                    pdf.ln()
                # Add total row
                pdf.set_font('Arial', 'B', 10)  # Bold for emphasis
                pdf.cell(90, 10, 'TOTAL', 1)
                pdf.cell(30, 10, str(total_marks), 1, align='C')
                pdf.cell(30, 10, '', 1)  # Empty grade column for total
                pdf.cell(40, 10, '', 1)  # Empty remarks column for total
                pdf.ln()

                # Add average row with grade and remarks
                pdf.cell(90, 10, 'AVERAGE', 1)
                pdf.cell(30, 10, str(average_marks), 1, align='C')
                pdf.cell(30, 10, grade, 1, align='C')
                pdf.cell(40, 10, remark, 1, align='C')
                pdf.ln()

                pdf.ln(10)
                pdf.cell(200, 10, f"Total Marks: {total_marks} | Average Marks: {average_marks}", ln=True)
                pdf.cell(200, 10, f"Remarks: {remarks}", ln=True)
                pdf.cell(200, 10, f"Class Coordinator: {coordinator_name} | Sign: {coordinator_sign} | Date: {coordinator_date}", ln=True)
                pdf.cell(200, 10, f"Head of Department: {hod_name} | Sign: {hod_sign} | Date: {hod_date}", ln=True)

                pdf_output = os.path.join(TEMP_FOLDER, f'transcript_{reg_no}.pdf')
                pdf.output(pdf_output)
                transcript_files.append(pdf_output)

            # Create ZIP file
            zip_filename = "transcripts.zip"
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for file in transcript_files:
                    zipf.write(file, os.path.basename(file))  # Add file to ZIP

            flash("Transcripts generated successfully! Download below.")
            return redirect(url_for('download_page'))  # Redirect to download page

        except Exception as e:
            flash(f"An error occurred: {str(e)}")
            return redirect(url_for('index'))  # Reload the form page

    return render_template('index.html')

@app.route('/download')
def download_page():
    return render_template('download.html')

@app.route('/download_zip')
def download_zip():
    zip_filename = "transcripts.zip"
    if os.path.exists(zip_filename):
        return send_file(zip_filename, as_attachment=True)
    else:
        flash("No ZIP file found. Please generate transcripts first.")
        return redirect(url_for('index'))
    
# Expose `app` as a WSGI-compatible entry point
def handler(event, context):
    return app(event, context)

if __name__ == '__main__':
    app.run()
    # (debug=True)
