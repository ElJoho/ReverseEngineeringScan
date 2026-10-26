// Pre-script: desactiva los analizadores que lanzan un decompilador por CPU.
// Con liborbbec_scan (113 MB) cada proceso usa ~2 GB y agota la RAM (ver overnight.sh).
//@category REA
import ghidra.app.script.GhidraScript;

public class DisableDecompilerAnalyzers extends GhidraScript {
    private static final String[] ANALYZERS = {
        "Decompiler Switch Analysis", "Decompiler Parameter ID",
        "Call Convention ID", "Objective-C Message Analyzer",
    };

    @Override
    protected void run() throws Exception {
        for (String name : ANALYZERS) {
            setAnalysisOption(currentProgram, name, "false");
            println("desactivado: " + name);
        }
    }
}
