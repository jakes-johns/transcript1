from flask import Flask, render_template, request, send_file, flash
import pandas as pd
from fpdf import FPDF
import os
import shutil
import zipfile

app = Flask(__name__)
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

# Route for input form
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            # Get common details
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

            # Get subjects
            subject_codes = request.form.getlist('subject_code[]')
            subjects = request.form.getlist('subject[]')

            # Get student details
            student_names = request.form.getlist('student_name[]')
            reg_nos = request.form.getlist('reg_no[]')

            # Create temporary directory for transcripts
            temp_dir = "temp_transcripts"
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)  # Remove previous files
            os.makedirs(temp_dir)

            # Generate transcripts for each student
            transcript_files = []
            for i in range(len(student_names)):
                student_name = student_names[i]
                reg_no = reg_nos[i]
                marks_input = request.form.getlist(f'marks_{i}[]')

                # Convert marks to integers
                marks = []
                for mark in marks_input:
                    try:
                        marks.append(int(mark.replace(',', '').strip()))  # Remove commas before conversion
                    except ValueError:
                        flash(f"Invalid mark '{mark}' for student {student_name}. Skipping.")
                        marks.append(0)  # Default to 0 if conversion fails

                # Ensure marks match subjects count
                if len(marks) != len(subjects):
                    flash(f"Error: Mismatch in subjects and marks for {student_name}. Skipping transcript.")
                    continue  # Skip this student

                total_marks = sum(marks)
                average_marks = round(total_marks / len(marks), 2)
                results = [(subject_codes[j], subjects[j], marks[j], *calculate_grade(marks[j])) for j in range(len(subjects))]

                # Generate PDF Transcript
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font('Arial', 'B', 12)

                # Add school logo (if exists)
                if os.path.exists('school_logo.jpg'):
                    pdf.image('school_logo.jpg', 10, 8, 33)

                pdf.cell(200, 10, school_name, ln=True, align='C')
                pdf.cell(200, 10, f"Student Transcript - {semester}", ln=True, align='C')
                pdf.cell(200, 10, f"Name: {student_name} | Reg No: {reg_no} | Class: {class_name}", ln=True, align='C')
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

                pdf.ln(10)
                pdf.cell(200, 10, f"Total Marks: {total_marks} | Average Marks: {average_marks}", ln=True)
                pdf.cell(200, 10, f"Remarks: {remarks}", ln=True)
                pdf.cell(200, 10, f"Class Coordinator: {coordinator_name} | Sign: {coordinator_sign} | Date: {coordinator_date}", ln=True)
                pdf.cell(200, 10, f"Head of Department: {hod_name} | Sign: {hod_sign} | Date: {hod_date}", ln=True)

                # Save the transcript in temp directory
                pdf_output = os.path.join(temp_dir, f'transcript_{reg_no}.pdf')
                pdf.output(pdf_output)
                transcript_files.append(pdf_output)

            # Create ZIP file
            zip_filename = "transcripts.zip"
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for file in transcript_files:
                    zipf.write(file, os.path.basename(file))  # Add file to ZIP

            # Cleanup: Remove temporary transcript files
            shutil.rmtree(temp_dir)

            return send_file(zip_filename, as_attachment=True)

        except Exception as e:
            flash(f"An error occurred: {str(e)}")
            return render_template('form.html')

    return render_template('form.html')

if __name__ == '__main__':
    app.run(debug=True)
