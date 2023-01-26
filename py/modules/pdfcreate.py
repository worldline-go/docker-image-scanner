import os, tarfile
from modules import colours, logs
from modules import dockerutils
from fpdf import FPDF
from docker.errors import APIError

class PDFConvertor:
    def get_detailed_report(container_id, image, report_log_file, pdf_folder):
        '''
         This function converts malware and compliance report files
         to PDF format to upload them as an artifact in Gitlab pipeline.
         Font was inserted in pre-build image to make it
         accessible during pipeline.
        '''

        font_name = "DejaVu"
        font_dir = "/usr/share/fonts"
        font_data = "DejaVuSansCondensed.ttf"

        for dirpath, _, font in os.walk(font_dir): # auto find font(.ttf) data path
            for fontname in font:
                 if font_data in fontname:
                     font_path = os.path.join(dirpath, fontname)
                     break

        if pdf_folder is not None:
            if not os.path.exists(pdf_folder):
                try:
                    os.makedirs(pdf_folder)
                except OSError:
                    dockerutils.command.kill_container(container_id)
                    raise
        else:
            raise Exception(colours.red("PDF folder name is not defined!"))

        image_name = image.split('/')[-1]
        report_log_format = f"{pdf_folder}/{image_name}-{container_id}"

        def copy_scanned_report(*args):
            try: # Copy report log file from on container to the host server.
                container = dockerutils.client.containers.get(container_id)
                bits, stat = container.get_archive(report_log_file)
                with open(report_log_format, 'wb') as file_handle:
                    for chunk in bits:
                        file_handle.write(chunk)
            except (APIError, IOError):
                raise

        def extract_scanned_report(*args):
            try: # Extracts tar formatted report file, and rename it with text format.
               tar_file = tarfile.open(report_log_format)
               tar_file.extractall(pdf_folder)
               tar_file_name = tar_file.getnames()
               if tar_file_name:
                   for file in tar_file_name:
                       os.rename(f"{pdf_folder}/{file}", report_log_format)
                       tar_file.close()
            except (tarfile.TarError, OSError):
                raise

        def convert_scanned_report(report_log_format):
            try:
               if os.path.getsize(report_log_format) > 0:
                   logs.event.logger.info("Converting report file to the PDF format." )
                   with open(report_log_format, "r+") as report_text:
                       pdf_file = report_text.read()
                       report_text = FPDF()
                       report_text.add_page()
                       report_text.set_xy(0, 0)
                       report_text.add_font(font_name, '', rf"{font_path}", uni=True)
                       report_text.set_font(font_name,'', 12.0)
                       report_text.multi_cell(0,5, pdf_file)
                       report_text.output(f"{report_log_format}.pdf", 'F')
                       print(colours.blue(f"Report file path: {report_log_format}.pdf"))
            except IOError:
                raise

        def remove_unused_log_report(report_log_format):
            if os.path.exists(f"{report_log_format}.pdf"):
                try: # Removes report log file on host server when PDF converting is done.
                    os.remove(report_log_format)
                except OSError:
                    raise

        copy_scanned_report(container_id, report_log_format, report_log_file)
        extract_scanned_report(report_log_format, pdf_folder)
        convert_scanned_report(report_log_format)
        remove_unused_log_report(report_log_format)
