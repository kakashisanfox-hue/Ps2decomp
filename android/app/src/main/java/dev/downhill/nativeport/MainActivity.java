package dev.downhill.nativeport;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.provider.DocumentsContract;
import android.view.Gravity;
import android.view.View;
import android.view.MotionEvent;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Color;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.FileInputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class MainActivity extends Activity {
    private static final int PICK_ISO = 410;
    private TextView log;
    private LinearLayout root;
    private boolean isoValidated = false;
    private String elfSummary = "";

    private static int u8(byte[] b, int off) { return b[off] & 255; }
    private static long le32(byte[] b, int off) {
        return (u8(b,off) | ((long)u8(b,off+1)<<8) | ((long)u8(b,off+2)<<16) | ((long)u8(b,off+3)<<24));
    }
    private static byte[] read(FileChannel ch, long pos, int length) throws Exception {
        if (length < 0 || length > 4*1024*1024) throw new IllegalArgumentException("Invalid read size");
        ByteBuffer b=ByteBuffer.allocate(length);
        while (b.hasRemaining()) {
            int n=ch.read(b,pos+b.position());
            if (n<=0) throw new java.io.EOFException("ISO truncated at "+pos);
        }
        return b.array();
    }
    private static String fileName(byte[] rec,int offset,int len) {
        String s=new String(rec,offset,len,StandardCharsets.US_ASCII);
        int semi=s.indexOf(';');
        return semi>=0?s.substring(0,semi):s;
    }
    private static final class Entry {
        final long lba,size; final boolean directory;
        Entry(long l,long s,boolean d){lba=l;size=s;directory=d;}
    }
    private static Entry find(FileChannel ch,Entry directory,String name) throws Exception {
        if(directory.size>8*1024*1024)throw new IllegalArgumentException("Directory too large");
        byte[] data=read(ch,directory.lba*2048,(int)directory.size);
        for(int i=0;i<data.length;) {
            int len=u8(data,i);
            if(len==0){i=((i/2048)+1)*2048;continue;}
            if(len<34 || i+len>data.length)throw new IllegalArgumentException("Malformed ISO9660 directory");
            int n=u8(data,i+32);
            if(33+n<=len) {
                String found=fileName(data,i+33,n);
                if(found.equalsIgnoreCase(name))
                    return new Entry(le32(data,i+2),le32(data,i+10),(u8(data,i+25)&2)!=0);
            }
            i+=len;
        }
        return null;
    }
    private void append(String s){log.append(s+"\n");}
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28,36,28,28);
        TextView title=new TextView(this);
        title.setText("DOWNHILL NATIVE — ISO DIAGNOSTIC");
        title.setTextSize(21);
        root.addView(title);
        Button choose=new Button(this);
        choose.setText("Selecionar ISO do Downhill");
        root.addView(choose);
        Button demo=new Button(this);
        demo.setText("Abrir protótipo de controles e gráficos (NÃO é o jogo)");
        root.addView(demo);
        demo.setOnClickListener(v->showPrototype());
        TextView notice=new TextView(this);
        notice.setText("Este APK lê a ISO e identifica o executável original. NÃO executa gameplay nem emula PS2.");
        notice.setPadding(0,12,0,12);
        root.addView(notice);
        ScrollView scroll=new ScrollView(this);
        log=new TextView(this);
        log.setTextSize(14);
        scroll.addView(log);
        root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        setContentView(root);
        append("Aguardando ISO...\n");
        choose.setOnClickListener(v->{
            Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT);
            pick.setType("*/*");
            pick.addCategory(Intent.CATEGORY_OPENABLE);
            startActivityForResult(pick,PICK_ISO);
        });
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request!=PICK_ISO||result!=RESULT_OK||data==null||data.getData()==null)return;
        Uri uri=data.getData();
        log.setText("ISO selecionada. Inspecionando...\n");
        new Thread(()->{
            try(ParcelFileDescriptor pfd=getContentResolver().openFileDescriptor(uri,"r");
                FileInputStream stream=new FileInputStream(pfd.getFileDescriptor())) {
                FileChannel ch=stream.getChannel();
                byte[] pvd=read(ch,16L*2048,2048);
                if(pvd[0]!=1 || !new String(pvd,1,5,StandardCharsets.US_ASCII).equals("CD001"))
                    throw new IllegalArgumentException("Not an ISO9660 data track (possibly compressed image)");
                Entry root=new Entry(le32(pvd,156+2),le32(pvd,156+10),true);
                Entry system=find(ch,root,"SYSTEM.CNF");
                if(system==null||system.directory||system.size>65536)
                    throw new IllegalArgumentException("SYSTEM.CNF missing or invalid");
                String cnf=new String(read(ch,system.lba*2048,(int)system.size),StandardCharsets.US_ASCII);
                Matcher m=Pattern.compile("(?im)^\\s*BOOT2?\\s*=\\s*cdrom0?:?[/\\\\]*([^;\\r\\n]+)").matcher(cnf);
                if(!m.find())throw new IllegalArgumentException("No BOOT/BOOT2 entry in SYSTEM.CNF");
                String path=m.group(1).trim().replace('\\','/');
                Entry current=root;
                for(String part:path.split("/")){
                    if(part.isEmpty())continue;
                    current=find(ch,current,part);
                    if(current==null)throw new IllegalArgumentException("Executable not found: "+part);
                }
                if(current.directory || current.size<52)throw new IllegalArgumentException("Invalid executable");
                byte[] elf=read(ch,current.lba*2048,52);
                if(elf[0]!=127||elf[1]!='E'||elf[2]!='L'||elf[3]!='F')
                    throw new IllegalArgumentException("BOOT target is not ELF");
                ByteBuffer head=ByteBuffer.wrap(elf).order(ByteOrder.LITTLE_ENDIAN);
                int machine=head.getShort(18)&65535;
                long entry=head.getInt(24)&0xffffffffL;
                String report="ISO9660: OK\nSYSTEM.CNF: OK\nBOOT: "+path+
                    "\nELF class: "+(elf[4]&255)+"\nMachine: "+machine+
                    "\nEntry: 0x"+Long.toHexString(entry).toUpperCase(Locale.ROOT)+
                    "\nSize: "+current.size+" bytes\n\nISO successfully inspected. Game execution is NOT implemented.";
                runOnUiThread(()->{isoValidated=true;elfSummary=report;log.setText(report);});
            }catch(Exception ex){
                runOnUiThread(()->log.setText("Falha ao analisar ISO: "+ex.getMessage()));
            }
        }).start();
    }
    // This is an intentionally separate graphics/input harness. It is NOT Downhill
    // gameplay and does not execute, interpret or recompile the PS2 executable.
    private void showPrototype() {
        final android.widget.FrameLayout frame=new android.widget.FrameLayout(this);
        final BikeView bike=new BikeView(this);
        frame.addView(bike);
        Button back=new Button(this);
        back.setText("Voltar para ISO");
        android.widget.FrameLayout.LayoutParams bp=new android.widget.FrameLayout.LayoutParams(-2,-2,Gravity.TOP|Gravity.END);
        frame.addView(back,bp);
        back.setOnClickListener(v->setContentView(root));
        setContentView(frame);
    }
    private final class BikeView extends View {
        private final Paint p=new Paint(3);
        private float steering=0f, speed=0f, distance=0f;
        private long last=System.nanoTime();
        BikeView(android.content.Context ctx){super(ctx);setFocusable(true);}
        private void paint(Canvas c,int color,float stroke){
            p.setColor(color);p.setStrokeWidth(stroke);p.setStyle(Paint.Style.STROKE);
        }
        @Override protected void onDraw(Canvas c){
            super.onDraw(c);
            final float w=getWidth(),h=getHeight();
            c.drawColor(Color.rgb(110,177,215));
            p.setStyle(Paint.Style.FILL);
            p.setColor(Color.rgb(70,123,65));
            c.drawRect(0,h*.4f,w,h,p);
            p.setColor(Color.rgb(102,82,58));
            android.graphics.Path trail=new android.graphics.Path();
            trail.moveTo(w*.44f,h*.4f);trail.lineTo(w*.56f,h*.4f);
            trail.lineTo(w*.95f,h);trail.lineTo(w*.05f,h);trail.close();
            c.drawPath(trail,p);
            p.setColor(Color.WHITE);p.setTextSize(Math.max(23,w*.038f));
            c.drawText("PROTÓTIPO GRÁFICO — NÃO É DOWNHILL",18,40,p);
            c.drawText(String.format(java.util.Locale.US,"Velocidade: %.0f  Distância: %.0f",speed,distance),18,75,p);
            c.drawText("Esquerda / direita: virar   |   Parte inferior: acelerar",18,h-26,p);
            float x=w*.5f+steering*w*.23f, y=h*.73f;
            paint(c,Color.BLACK,Math.max(4,w*.009f));
            c.drawCircle(x-27,y+34,26,p);c.drawCircle(x+27,y+34,26,p);
            c.drawLine(x-27,y+34,x,y-10,p);c.drawLine(x,y-10,x+27,y+34,p);
            c.drawLine(x-27,y+34,x+27,y+34,p);
            paint(c,Color.YELLOW,Math.max(5,w*.013f));
            c.drawLine(x,y-10,x+5,y-47,p);
            paint(c,Color.BLUE,Math.max(8,w*.018f));
            c.drawLine(x+5,y-47,x+16,y-75,p);
            p.setStyle(Paint.Style.FILL);p.setColor(Color.rgb(230,180,120));
            c.drawCircle(x+16,y-87,13,p);
            long now=System.nanoTime();
            float dt=Math.min(.05f,(now-last)/1_000_000_000f);last=now;
            distance+=speed*dt;
            speed=Math.max(0,speed-8*dt);
            postInvalidateDelayed(33);
        }
        @Override public boolean onTouchEvent(MotionEvent e){
            if(e.getAction()==MotionEvent.ACTION_DOWN||e.getAction()==MotionEvent.ACTION_MOVE){
                float x=e.getX()/Math.max(1,getWidth()), y=e.getY()/Math.max(1,getHeight());
                steering=Math.max(-1,Math.min(1,(x-.5f)*2));
                if(y>.5f)speed=Math.min(80,speed+1.8f);
                invalidate();return true;
            }
            return true;
        }
    }

}
