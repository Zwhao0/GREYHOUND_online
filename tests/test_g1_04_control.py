"""CPU-only socket collector bounds and framing; no GPU evidence."""
import socket
import sys
import threading
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from g1_04_control import run,receive
import time

class ControlTests(unittest.TestCase):
    def test_invalid_limits_fail_before_network(self):
        for extra in ({'count':True},{'count':120001},{'interval':0},{'duration':float('nan')},{'timeout':121}):
            args=dict(role='client',address='127.0.0.1',port=1,identity={},duration=1,count=100,interval=.0005,timeout=8)
            args.update(extra)
            with self.assertRaises(ValueError):run(**args)

    def test_loopback_bounded_session_and_independent_server_stamps(self):
        # Identity is a CPU fixture because macOS has no Linux /proc namespaces.
        identity=dict(run='CPU',epoch='fixture',node='node-a')
        out={};ready=threading.Event()
        # Bind the selected port while arranging startup; no fixed port dependency.
        listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1];listener.close()
        def server():
            try:out['server']=run('server','127.0.0.1',port,{**identity,'node':'node-b'},1,5000,.0005,8)
            except Exception as exc:out['error']=exc
        t=threading.Thread(target=server);t.start()
        # Retry only connection establishment in this CPU test, never training.
        client=None
        for _ in range(100):
            try:
                client=run('client','127.0.0.1',port,identity,1,5000,.0005,8);break
            except ConnectionRefusedError:time.sleep(.001)
        t.join(9)
        self.assertFalse(t.is_alive());self.assertNotIn('error',out)
        self.assertTrue(client['complete']);self.assertEqual(client['stop_reason'],'DURATION_LIMIT')
        self.assertLessEqual(client['count'],5000)
        self.assertEqual(out['server']['exchanges'],[{k:s[k] for k in ('index','t1','t2','t3')} for s in client['exchanges']])

    def test_malformed_multiple_frames_are_rejected(self):
        a,b=socket.socketpair()
        with a,b:
            a.sendall(b'{}\n{}\n')
            with self.assertRaises(ValueError):receive(b,time.monotonic()+1)
