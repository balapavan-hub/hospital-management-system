import io
from datetime import datetime
from decimal import Decimal
import pandas as pd

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class ReportService:
    @staticmethod
    def generate_prescription_pdf(prescription):
        """
        Generate a professional PDF for a doctor's prescription.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )
        
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            textColor=colors.HexColor('#1E3A8A'), # Navy Blue
            alignment=1 # Centered
        )
        
        subtitle_style = ParagraphStyle(
            'DocSubTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=10,
            leading=12,
            textColor=colors.HexColor('#4B5563'),
            alignment=1
        )
        
        h2_style = ParagraphStyle(
            'H2',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#1E3A8A'),
            spaceBefore=10,
            spaceAfter=6
        )
        
        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=12,
            textColor=colors.HexColor('#1F2937')
        )
        
        value_style = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            textColor=colors.HexColor('#4B5563')
        )
        
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#1F2937')
        )
        
        story = []
        
        # 1. Hospital Header
        story.append(Paragraph("MediCare Hospital", title_style))
        story.append(Paragraph("123 Health Care Blvd, Medical District | Phone: +91 98765 43210 | info@medicare.com", subtitle_style))
        story.append(Spacer(1, 15))
        
        # Divider Line
        line_table = Table([[""]], colWidths=[doc.width])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,-1), 2, colors.HexColor('#1E3A8A')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 15))
        
        # 2. Metadata: Doctor and Patient Info block
        appt = prescription.appointment
        date_str = prescription.created_at.strftime('%d-%b-%Y')
        
        meta_data = [
            [Paragraph("Patient Name:", label_style), Paragraph(prescription.patient.full_name, value_style),
             Paragraph("Date:", label_style), Paragraph(date_str, value_style)],
            [Paragraph("Age / Gender:", label_style), Paragraph(f"{prescription.patient.age} Y / {prescription.patient.gender}", value_style),
             Paragraph("Doctor:", label_style), Paragraph(prescription.doctor.full_name, value_style)],
            [Paragraph("Patient Phone:", label_style), Paragraph(prescription.patient.phone, value_style),
             Paragraph("Department:", label_style), Paragraph(prescription.doctor.department.name, value_style)]
        ]
        
        meta_table = Table(meta_data, colWidths=[doc.width*0.18, doc.width*0.32, doc.width*0.18, doc.width*0.32])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 20))
        
        # 3. Symptoms and Diagnosis
        story.append(Paragraph("Symptoms", h2_style))
        story.append(Paragraph(prescription.symptoms or "None reported", body_style))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph("Diagnosis", h2_style))
        story.append(Paragraph(prescription.diagnosis or "N/A", body_style))
        story.append(Spacer(1, 15))
        
        # 4. Rx (Medicines)
        story.append(Paragraph("Rx (Medicines prescribed)", h2_style))
        
        rx_header_style = ParagraphStyle(
            'RxHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.white
        )
        
        rx_data = [
            [Paragraph("Medicine Name", rx_header_style), 
             Paragraph("Morning", rx_header_style), 
             Paragraph("Afternoon", rx_header_style), 
             Paragraph("Night", rx_header_style), 
             Paragraph("Duration", rx_header_style)]
        ]
        
        for med in prescription.medicines:
            rx_data.append([
                Paragraph(med.medicine_name, body_style),
                Paragraph("1" if med.dosage_morning else "0", body_style),
                Paragraph("1" if med.dosage_afternoon else "0", body_style),
                Paragraph("1" if med.dosage_night else "0", body_style),
                Paragraph(f"{med.duration_days} Days", body_style)
            ])
            
        if len(prescription.medicines) == 0:
            rx_data.append([Paragraph("No medicines prescribed", body_style), "", "", "", ""])
            
        rx_table = Table(rx_data, colWidths=[doc.width*0.4, doc.width*0.15, doc.width*0.15, doc.width*0.15, doc.width*0.15])
        rx_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
            ('PADDING', (0,0), (-1,-1), 8),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ]))
        story.append(rx_table)
        story.append(Spacer(1, 20))
        
        # 5. Follow-up and Remarks
        bottom_data = [
            [Paragraph("Remarks / Advice:", label_style), Paragraph(prescription.remarks or "None", body_style)],
            [Paragraph("Follow-up Date:", label_style), Paragraph(prescription.follow_up_date.strftime('%d-%b-%Y') if prescription.follow_up_date else "As needed", body_style)]
        ]
        bottom_table = Table(bottom_data, colWidths=[doc.width*0.25, doc.width*0.75])
        bottom_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(bottom_table)
        
        story.append(Spacer(1, 50))
        
        # Signature block
        sig_data = [
            ["", "_______________________"],
            ["", f"{prescription.doctor.full_name}"],
            ["", f"{prescription.doctor.specialization}"]
        ]
        sig_table = Table(sig_data, colWidths=[doc.width*0.6, doc.width*0.4])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ]))
        story.append(KeepTogether(sig_table))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def generate_invoice_pdf(bill):
        """
        Generate a professional PDF Invoice / Bill.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )
        
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#10B981'), # Emerald Green
            alignment=0
        )
        
        subtitle_style = ParagraphStyle(
            'DocSubTitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#6B7280'),
        )
        
        invoice_header_style = ParagraphStyle(
            'InvHeader',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#1F2937'),
            alignment=2 # Right aligned
        )
        
        h2_style = ParagraphStyle(
            'H2',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#1F2937'),
            spaceBefore=10,
            spaceAfter=6
        )
        
        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=11,
            textColor=colors.HexColor('#1F2937')
        )
        
        value_style = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=11,
            textColor=colors.HexColor('#4B5563')
        )
        
        th_style = ParagraphStyle(
            'TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.white
        )
        
        body_style = ParagraphStyle(
            'Body', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor('#1F2937')
        )
        
        body_right_style = ParagraphStyle(
            'BodyRight', parent=body_style, alignment=2
        )
        
        story = []
        
        # 1. Logo and Invoice Header side-by-side
        header_data = [
            [Paragraph("MediCare Hospital", title_style), Paragraph("INVOICE", invoice_header_style)],
            [Paragraph("123 Health Care Blvd, Medical District\nPhone: +91 98765 43210 | info@medicare.com", subtitle_style),
             Paragraph(f"Invoice #: MC-{bill.id:06d}\nDate: {bill.created_at.strftime('%d-%b-%Y')}\nPayment Status: {bill.status.upper()}", subtitle_style)]
        ]
        header_table = Table(header_data, colWidths=[doc.width*0.5, doc.width*0.5])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 15))
        
        # Divider Line
        line_table = Table([[""]], colWidths=[doc.width])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#10B981')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 15))
        
        # 2. Bill To & Doctor details
        bill_to_data = [
            [Paragraph("BILL TO:", label_style), Paragraph("CONSULTING DOCTOR:", label_style)],
            [
                Paragraph(f"<b>{bill.patient.full_name}</b><br/>Phone: {bill.patient.phone}<br/>Address: {bill.patient.address or 'N/A'}", value_style),
                Paragraph(f"<b>{bill.appointment.doctor.full_name if bill.appointment else 'Hospital OPD'}</b><br/>Department: {bill.appointment.doctor.department.name if (bill.appointment and bill.appointment.doctor) else 'General'}", value_style)
            ]
        ]
        bill_to_table = Table(bill_to_data, colWidths=[doc.width*0.5, doc.width*0.5])
        bill_to_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(bill_to_table)
        story.append(Spacer(1, 20))
        
        # 3. Itemized Charges Table
        items_data = [
            [Paragraph("Sl No.", th_style), Paragraph("Description", th_style), Paragraph("Amount (INR)", th_style)]
        ]
        
        row_num = 1
        subtotal = Decimal('0.00')
        
        # Add consultation fee if active
        if bill.consultation_fee > 0:
            items_data.append([
                Paragraph(str(row_num), body_style),
                Paragraph("Doctor Consultation Charges", body_style),
                Paragraph(f"{bill.consultation_fee:,.2f}", body_right_style)
            ])
            row_num += 1
            subtotal += Decimal(str(bill.consultation_fee))
            
        # Add medicine charges if active
        if bill.medicine_charges > 0:
            items_data.append([
                Paragraph(str(row_num), body_style),
                Paragraph("Prescribed Medicine Charges", body_style),
                Paragraph(f"{bill.medicine_charges:,.2f}", body_right_style)
            ])
            row_num += 1
            subtotal += Decimal(str(bill.medicine_charges))
            
        # Add lab charges if active
        if bill.lab_charges > 0:
            items_data.append([
                Paragraph(str(row_num), body_style),
                Paragraph("Laboratory / Diagnostic Tests", body_style),
                Paragraph(f"{bill.lab_charges:,.2f}", body_right_style)
            ])
            row_num += 1
            subtotal += Decimal(str(bill.lab_charges))
            
        # Add other charges if active
        if bill.other_charges > 0:
            items_data.append([
                Paragraph(str(row_num), body_style),
                Paragraph("Other Ward / Hospital Services", body_style),
                Paragraph(f"{bill.other_charges:,.2f}", body_right_style)
            ])
            row_num += 1
            subtotal += Decimal(str(bill.other_charges))
            
        items_table = Table(items_data, colWidths=[doc.width*0.12, doc.width*0.63, doc.width*0.25])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')), # Dark Grey header
            ('PADDING', (0,0), (-1,-1), 8),
            ('ALIGN', (2,0), (2,-1), 'RIGHT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 15))
        
        # 4. Totals Block (Subtotal, GST, Discount, Grand Total)
        totals_data = [
            [Paragraph("Subtotal:", label_style), Paragraph(f"INR {subtotal:,.2f}", value_style)],
            [Paragraph("GST (18%):", label_style), Paragraph(f"INR {bill.gst:,.2f}", value_style)],
            [Paragraph("Discount:", label_style), Paragraph(f"- INR {bill.discount:,.2f}", value_style)],
            [Paragraph("Grand Total:", label_style), Paragraph(f"INR {bill.grand_total:,.2f}", label_style)]
        ]
        
        totals_table = Table(totals_data, colWidths=[doc.width*0.75, doc.width*0.25])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('PADDING', (0,0), (-1,-1), 4),
            ('LINEBELOW', (0,3), (1,3), 1, colors.HexColor('#1F2937')),
            ('BACKGROUND', (0,3), (1,3), colors.HexColor('#F1F5F9')),
        ]))
        story.append(totals_table)
        story.append(Spacer(1, 30))
        
        # Footer notice
        notice_style = ParagraphStyle(
            'Notice',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#6B7280'),
            alignment=1
        )
        story.append(Paragraph("This is a computer-generated invoice and does not require a physical signature.", notice_style))
        story.append(Paragraph("Thank you for choosing MediCare Hospital. Get Well Soon!", notice_style))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def export_excel(data_dict, sheet_name="Report"):
        """
        Generic helper to export a pandas DataFrame to an Excel spreadsheet file bytes.
        """
        df = pd.DataFrame(data_dict)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def export_csv(data_dict):
        """
        Generic helper to export a dictionary data structure to CSV format bytes.
        """
        df = pd.DataFrame(data_dict)
        csv_str = df.to_csv(index=False)
        return csv_str.encode('utf-8')
