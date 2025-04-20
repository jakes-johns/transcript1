from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import zipfile
import os
import re
import pandas as pd
from fpdf import FPDF
from pathlib import Path
import logging
from werkzeug.utils import secure_filename


app = Flask(__name__)  # Set correct template path
app.secret_key = 'your_secret_key'  # Needed for flashing messages

# Initialize logging
logging.basicConfig(level=logging.DEBUG)

def sanitize_filename(filename):
    """Remove or replace invalid characters in filenames."""
    return re.sub(r'[^\w\d-]', '_', filename)  # Replace special characters with '_'

# Function to calculate grades and remarks.
def calculate_grade(marks):
    if marks <= 0:
        return '-', 'NOT DONE'
    elif 1 <= marks <= 49:
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
            # Get common details
            school_name = request.form.get('school_name', 'Unknown School')
            department = request.form.get('department', 'UNKNOWN DEPARTMENT')
            program = request.form.get('program', 'UNKNOWN PROGRAM')
            year = request.form.get('year', 'unknown year')
            semester = request.form.get('semester', 'Unknown Semester')
            class_name = request.form.get('class_name', 'Unknown Class')
            transcript_date = request.form.get('transcript_date', 'N/A')
            remarks = request.form.get('remarks', 'No remarks provided')
            coordinator_name = request.form.get('coordinator_name', 'N/A')
            coordinator_date = request.form.get('coordinator_date', 'N/A')
            hod_name = request.form.get('hod_name', 'N/A')
            hod_date = request.form.get('hod_date', 'N/A')

            # Get subject codes and names manually entered by user
            subject_codes = request.form.getlist('subject_code[]')
            subjects = request.form.getlist('subject[]')

            # Initialize containers
            student_names = []
            reg_nos = []
            marks_list = []

            # Check if Excel file was uploaded
            uploaded_file = request.files.get('excel_file')
            if uploaded_file and uploaded_file.filename.endswith(('.xlsx', '.xls')):
                import pandas as pd
                # Load the Excel file with multiple sheets
                xls = pd.ExcelFile(uploaded_file)

                # Check if required sheets exist
                if 'Students' not in xls.sheet_names or 'Subjects' not in xls.sheet_names:
                    flash("Excel file must contain both 'Students' and 'Subjects' sheets.")
                    return redirect(url_for('index'))

                # Read the sheets
                students_df = pd.read_excel(xls, sheet_name='Students')
                subjects_df = pd.read_excel(xls, sheet_name='Subjects')

                # Validate columns in the 'Students' sheet
                if 'Student Name' not in students_df.columns or 'Reg No' not in students_df.columns:
                    flash("The 'Students' sheet must contain 'Student Name' and 'Reg No' columns.")
                    return redirect(url_for('index'))

                # Extract subjects from the 'Subjects' sheet
                if 'Code' not in subjects_df.columns or 'Subject' not in subjects_df.columns:
                    flash("The 'Subjects' sheet must contain 'Code' and 'Subject' columns.")
                    return redirect(url_for('index'))

                subject_codes = subjects_df['Code'].tolist()
                subjects = subjects_df['Subject'].tolist()

                # Extract students and their marks
                for _, row in students_df.iterrows():
                    student_names.append(row['Student Name'])
                    reg_nos.append(row['Reg No'])

                    student_marks = []
                    for code in subject_codes:
                        marks_column_name = f"{code}_marks"
                        try:
                            student_marks.append(int(row[marks_column_name]))
                        except KeyError:
                            flash(f"Missing column '{marks_column_name}' for student {row['Student Name']}")
                            student_marks.append(0)
                        except ValueError:
                            flash(f"Invalid mark for subject code {code}. Skipping this entry.")
                            student_marks.append(0)

                    marks_list.append(student_marks)

            else:
                # Manual input fallback
                student_names = request.form.getlist('student_name[]')
                reg_nos = request.form.getlist('reg_no[]')

                for i in range(len(student_names)):
                    raw_marks = request.form.getlist(f'marks_{i}[]')
                    marks = []
                    for mark in raw_marks:
                        try:
                            cleaned_mark = str(mark).replace(',', '').strip()
                            marks.append(int(cleaned_mark))
                        except ValueError:
                            flash(f"Invalid mark '{mark}' for student {student_names[i]}. Skipping this entry.")
                            marks.append(0)
                    marks_list.append(marks)

            # Generate transcripts for each student
            transcript_files = []
            for i in range(len(student_names)):
                student_name = student_names[i]
                reg_no = str(reg_nos[i]).strip()  # Keep Reg No unchanged inside the transcript
                marks = marks_list[i]

                total_marks = sum(marks)
                average_marks = round(total_marks / len(marks), 2)
                results = [(subject_codes[j], subjects[j], marks[j], *calculate_grade(marks[j])) for j in range(len(subjects))]

                # Generate PDF Transcript
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font('Arial', 'B', 12)

                # Add watermarks
                BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get the current script directory
                watermark_top_right = os.path.join(BASE_DIR, "static", "watermark1.PNG")
                watermark_bottom = os.path.join(BASE_DIR, "static", "watermark2.PNG")

                print(f"Checking: {watermark_top_right} -> Exists? {os.path.exists(watermark_top_right)}")
                print(f"Checking: {watermark_bottom} -> Exists? {os.path.exists(watermark_bottom)}")

                # debugging statement for watermark
                if not os.path.exists(watermark_top_right):
                    print(f"Error: {watermark_top_right} not found!")

                if not os.path.exists(watermark_bottom):
                    print(f"Error: {watermark_bottom} not found!")

               # Define different sizes for each watermark
                top_right_width = 80  # Width for top right watermark
                top_right_height = 31  # Height for top right watermark

                bottom_width = pdf.w  # Width for bottom watermark
                bottom_height = 30  # Height for bottom watermark.

                # Add the first watermark (top-right corner, touching borders)
                if os.path.exists(watermark_top_right):
                    pdf.image(watermark_top_right, x=pdf.w - top_right_width, y=0, w=top_right_width, h=top_right_height)

                # Add the second watermark (full-width bottom)
                if os.path.exists(watermark_bottom):
                    pdf.image(watermark_bottom, x=0, y=pdf.h - bottom_height, w=bottom_width, h=bottom_height)

                # Add school logo (ensure file exists)
                logo_path = 'kmtc_logo.jpeg'  # Update with correct path
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
                pdf.cell(200, 5, f"KENYA MEDICAL TRAINING COLLEGE", ln=True, align='C')
                pdf.cell(200, 5, f"QUALITY MANAGEMENT SYSTEMS", ln=True, align='C')
                pdf.cell(200, 5, f"ASSESSMENT OF STUDENT'S LEARNING", ln=True, align='C')
                pdf.cell(200, 5, f"DEPARTMENT OF {department}", ln=True, align='C')
                pdf.cell(200, 5, f"INDIVIDUAL STUDENT'S SCORE SHEET", ln=True, align='C')
                pdf.cell(200, 5, f"SEMESTER {semester}", ln=True, align='C')
                pdf.cell(200, 5, f"College:  {school_name}", ln=True)

                pdf.cell(120, 5, f"Name:  {student_name}", ln=False)
                pdf.cell(80, 5, f"College No.:  {reg_no}", ln=True)

                pdf.cell(120, 5, f"Class:  {class_name}", ln=False)
                pdf.cell(80, 5, f"Year Of Study:  {year}", ln=True)

                # pdf.cell(120, 5, f"Program:  {program}", ln=False)
                pdf.cell(200, 5, f"Date:  {transcript_date}", ln=True)  #CHANGED THE MEASUREMNTS FROM 80,5 TO 200,5
                pdf.ln(3)

                # Table headers
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(30, 10, 'CODE', 1) #edited the name
                pdf.cell(70, 10, 'SUBJECTS', 1) #edited the row width and name 60 to 70. CHANGED MODULES TO SUBJECTS
                pdf.cell(30, 10, 'MARKS', 1)
                pdf.cell(20, 10, 'GRADE', 1) #edited the row width from 30 to 20
                pdf.cell(40, 10, 'REMARKS', 1)
                pdf.ln()

                # Table content
                pdf.set_font('Arial', '', 10)
                for code, subj, mark, grade, remark in results:
                    pdf.cell(30, 7, code, 1, align='C')
                    pdf.cell(70, 7, subj, 1, align='C') #edited the row width and name 60 to 70
                    pdf.cell(30, 7, str(mark), 1, align='C')
                    pdf.cell(20, 7, grade, 1, align='C') #edited the row width from 30 to 20
                    pdf.cell(40, 7, remark, 1, align='C')
                    pdf.ln()
                # Add total row
                pdf.set_font('Arial', 'B', 10)  # Bold for emphasis
                pdf.cell(100, 8, 'TOTAL', 1)
                pdf.cell(30, 8, str(total_marks), 1, align='C')
                pdf.cell(20, 8, '', 1)  # Empty grade column for total
                pdf.cell(40, 8, '', 1)  # Empty remarks column for total
                pdf.ln()

               # Add average row with grade and remarks
                average_grade, average_remark = calculate_grade(average_marks)  # Fix missing grading for average
                pdf.cell(100, 8, 'AVERAGE', 1)
                pdf.cell(30, 8, str(average_marks), 1, align='C')
                pdf.cell(20, 8, average_grade, 1, align='C')
                pdf.cell(40, 8, average_remark, 1, align='C')
                pdf.ln()

                pdf.ln(1)
                
                # General Remarks
                pdf.cell(200, 7, f"General Remarks By Class Coordinator: {remarks}", ln=True)

                # Student Signature
                pdf.cell(100, 7, f"STUDENT'S SIGN:............................................................", ln=False)
                pdf.cell(50, 7, f"DATE:.............................", ln=True)

                # Class Coordinator Line
                pdf.cell(100, 7, f"CLASS COORDINATOR:   {coordinator_name}", ln=False)  # Fixed width for name
                pdf.cell(50, 7, f"SIGN:..............................", ln=False)  # Fixed width for signature
                pdf.cell(40, 7, f"DATE: {coordinator_date}", ln=True)  # Moves to next line after date

                # Head of Department Line
                pdf.cell(100, 5, f"HEAD OF DEPARTMENT:   {hod_name}", ln=False)  # Same width as Coordinator
                pdf.cell(50, 5, f"SIGN:..............................", ln=False)  # Same width as Coordinator SIGN
                pdf.cell(40, 5, f"DATE: {hod_date}", ln=True)  # Moves to next line after date

                sanitized_reg_no = sanitize_filename(reg_no)  # Use only for the filename
                pdf_output = os.path.join(TEMP_FOLDER, f'transcript_{sanitized_reg_no}.pdf')

                print(f"Saving transcript to: {pdf_output}")  # Debugging statement

                pdf.output(pdf_output)

                if os.path.exists(pdf_output):
                    print(f"Transcript saved successfully: {pdf_output}")
                else:
                    print(f"Error: File not created - {pdf_output}")

                pdf.output(pdf_output)
                transcript_files.append(pdf_output)

            # Create ZIP file
            zip_filename = "transcripts.zip"
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for file in transcript_files:
                    if os.path.exists(file):  # Ensure file exists before adding to ZIP
                        zipf.write(file, os.path.basename(file))
                    else:
                        print(f"Skipping missing file: {file}")  # Debugging statement


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