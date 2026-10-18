package dev.downhill.nativeport;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;

public final class MainActivity extends Activity {
    static { System.loadLibrary("downhill_bridge"); }
    private static native String status();
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        TextView view = new TextView(this);
        view.setText("Downhill native research shell\n" + status() + "\nNo game code included.");
        view.setTextSize(18);
        view.setPadding(32, 48, 32, 32);
        setContentView(view);
    }
}
