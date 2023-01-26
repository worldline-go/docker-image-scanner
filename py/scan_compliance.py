import subprocess, os
from modules import packages, dockerutils
from modules import time, logs, pdfcreate

class lynis:
    # Start the compliance checking progress
    def run_lynis_scan(container_id, lynis_path, report_log_file):
        try:
            lynis_cmd = f"'./lynis audit system --log-file '{report_log_file}"
            lynis_scan_result = subprocess.Popen(
            [f"{packages.docker_cmd} -w {lynis_path} {container_id} /bin/sh -c {lynis_cmd}"],
                shell=True, encoding='utf-8')
            lynis_scan_result.wait()
            if lynis_scan_result.returncode != 0:
                raise Exception # Stop process if scan result is not finished successfully.
        except subprocess.CalledProcessError:
            raise

def start_compliance_scan():
  report_log_file="/tmp/lynis.log"

  images = dockerutils.command.get_quarantined_images()
  image_count = len(images)

  if images is None:
      raise Exception("Cannot find any image in quarantine!")
  else:
      for image in images:
          logs.event.logger.info("[1/5] Spin-up container from quarantine for compliance scan: %s" % image)
          container_id = dockerutils.command.start_container(image)

          logs.event.logger.info("[2/5] Health check of container before compliance scan: %s" % image)
          dockerutils.command.pre_check_result(image, container_id)
          logs.event.logger.info("[3/5] Adding compliance scanner source in target container: %s" % image)
          dockerutils.command.copy_files_to_container(container_id, "/opt/lynis.tar.gz", "/")

          logs.event.logger.info("[4/5] Detecting missing packages to setup before compliance scan: %s" % image)
          packages.MissingPackage.add_package(container_id, change_pkg_manager=False)

          logs.event.logger.info("[5/5] Compliance analyzing:\nContainer ID: %s %s %s", container_id, '\nImage Name:', image)
          lynis.run_lynis_scan(container_id, "/opt/lynis/", report_log_file)

          compliance_folder = os.environ.get('COMPLIANCE_REPORT_FOLDER')
          pdfcreate.PDFConvertor.get_detailed_report(container_id, image, report_log_file, compliance_folder)
          time.WaitNextProcess.set_sleep_time(3, image_count)
if __name__ == "__main__":
  start_compliance_scan()
