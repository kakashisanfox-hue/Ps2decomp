package dev.downhill.nativeport;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.provider.DocumentsContract;
import android.view.Gravity;
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
        LinearLayout root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28,36,28,28);
        TextView title=new TextView(this);
        title.setText("DOWNHILL NATIVE — ISO DIAGNOSTIC");
        title.setTextSize(21);
        root.addView(title);
        Button choose=new Button(this);
        choose.setText("Selecionar ISO do Downhill");
        root.addView(choose);
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
                runOnUiThread(()->log.setText(report));
            }catch(Exception ex){
                runOnUiThread(()->log.setText("Falha ao analisar ISO: "+ex.getMessage()));
            }
        }).start();
    }
}
