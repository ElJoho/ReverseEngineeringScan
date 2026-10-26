// Post-script: decompila las funciones cuyo nombre cumple una regex.
// Argumentos: <regex> <directorio de salida>. Escribe un .c por función e index.tsv.
// Usa un solo decompilador (sin paralelismo) para no agotar la RAM.
//@category REA
import java.io.File;
import java.io.PrintWriter;
import java.util.regex.Pattern;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;

public class DecompileMatching extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        Pattern pattern = Pattern.compile(args[0]);
        File outDir = new File(args[1]);
        outDir.mkdirs();

        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        int count = 0;
        try (PrintWriter index = new PrintWriter(new File(outDir, "index.tsv"))) {
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                if (monitor.isCancelled()) break;
                String name = f.getName(true);
                if (!pattern.matcher(name).find()) continue;
                DecompileResults res = decomp.decompileFunction(f, 120, monitor);
                String code = res.decompileCompleted()
                    ? res.getDecompiledFunction().getC()
                    : "// fallo: " + res.getErrorMessage() + "\n";
                String safe = name.replaceAll("[^A-Za-z0-9_.-]", "_");
                if (safe.length() > 180) safe = safe.substring(0, 180);  // límite de 255 bytes por nombre
                String file = safe + "@" + f.getEntryPoint() + ".c";
                try (PrintWriter out = new PrintWriter(new File(outDir, file))) {
                    out.print(code);
                }
                index.printf("%s\t%s\t%d\t%s%n", f.getEntryPoint(), name, f.getBody().getNumAddresses(), file);
                count++;
            }
        } finally {
            decomp.dispose();
        }
        println("decompiladas: " + count + " -> " + outDir);
    }
}
