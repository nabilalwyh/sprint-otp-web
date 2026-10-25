import unittest
import pandas as pd
from etl.transform import normalize_phone, build_report
class TestSprintOtp(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_phone("628123456789"), "8123456789")
        self.assertEqual(normalize_phone("08123456789"), "8123456789")
    def test_all_eight_indicators(self):
        sprint=pd.DataFrame([{"recipient":"628123456789","provider":"","divisi":"","client_name":"","name-u":"","masking":"","content":"","send_status":"","delivery_status":"","messagecount":1,"service":"","country":"","ref_id":"","time_dbrecv":"","time_send":"","time_sent":"","time_delivery":""}])
        users={"MDIN":pd.DataFrame({"PHONE":["08123456789"]}),"IB":pd.DataFrame({"NO_HP":["08123456789"]}),"MQRIS":pd.DataFrame({"PHONE":["08123456789"]})}
        def src(col): return pd.DataFrame({col:["628123456789","08123456789"]})
        report,_=build_report(sprint,users,src("phone"),src("phone"),src("MOBILE_NUMBER"),src("phone"),src("phone"))
        self.assertEqual(report.loc[0,"TOTAL"],8)
if __name__ == "__main__": unittest.main()
