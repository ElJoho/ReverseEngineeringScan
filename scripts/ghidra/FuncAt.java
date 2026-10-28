// Post-script: imprime la función que contiene cada dirección dada (hex, sin 0x).
// Útil para ubicar constantes encontradas con objdump (en __TEXT, dirección == offset del archivo).
// Uso: analyzeHeadless <proyecto> <nombre> -process <bin> -noanalysis -readOnly -postScript FuncAt.java a8a00 aa85d
//@category REA
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;

public class FuncAt extends GhidraScript {
    @Override
    protected void run() throws Exception {
        for (String a : getScriptArgs()) {
            Function f = getFunctionContaining(toAddr(Long.parseLong(a, 16)));
            println("FUNCAT " + a + " -> " + (f == null ? "?" : f.getName(true) + " @" + f.getEntryPoint()));
        }
    }
}
