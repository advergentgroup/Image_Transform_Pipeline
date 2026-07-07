/**
 * Image Trace via Adobe Illustrator (ExtendScript).
 * Placeholders are replaced by Python before execution.
 */
#target illustrator

(function () {
    var INPUT = "__INPUT__";
    var OUTPUT = "__OUTPUT__";
    var MAX_COLORS = __COLORS__;
    var NOISE_FIDELITY = __NOISE_FIDELITY__;
    var PATH_FIDELITY = __PATH_FIDELITY__;
    var CORNER_FIDELITY = __CORNER_FIDELITY__;
    var EXPORT_SCALE = __EXPORT_SCALE__;
    var TRACING_METHOD = __TRACING_METHOD__;
    var ERR = "__ERR__";

    function writeError(message) {
        var errFile = new File(ERR);
        errFile.encoding = "UTF-8";
        errFile.open("w");
        errFile.write(String(message));
        errFile.close();
    }

    function removeIfExists(file) {
        if (file.exists) {
            file.remove();
        }
    }

    try {
        var inputFile = new File(INPUT);
        var outputFile = new File(OUTPUT);
        var errFile = new File(ERR);

        removeIfExists(outputFile);
        removeIfExists(errFile);

        if (!inputFile.exists) {
            throw new Error("Input file not found: " + INPUT);
        }

        var doc = app.documents.add();
        var placed = doc.placedItems.add();
        placed.file = inputFile;
        placed.embed();

        if (doc.rasterItems.length === 0) {
            throw new Error("No raster item after embed");
        }

        var raster = doc.rasterItems[0];
        var plugin = raster.trace();
        var tracing = plugin.tracing;
        var opts = tracing.tracingOptions;

        opts.tracingMode = TracingModeType.TRACINGMODECOLOR;
        opts.tracingColorTypeValue = TracingColorType.TRACINGLIMITEDCOLOR;
        opts.tracingColors = MAX_COLORS;
        opts.tracingMethod = TRACING_METHOD;
        opts.noiseFidelity = NOISE_FIDELITY;
        opts.pathFidelity = PATH_FIDELITY;
        opts.cornerFidelity = CORNER_FIDELITY;
        opts.ignoreWhite = true;
        opts.snapCurveToLines = true;
        opts.fills = true;
        opts.strokes = false;

        tracing.expandTracing();

        for (var i = doc.rasterItems.length - 1; i >= 0; i--) {
            doc.rasterItems[i].remove();
        }

        var exportOpts = new ExportOptionsPNG24();
        exportOpts.transparency = true;
        exportOpts.antiAliasing = false;
        exportOpts.horizontalScale = EXPORT_SCALE;
        exportOpts.verticalScale = EXPORT_SCALE;

        doc.exportFile(outputFile, ExportType.PNG24, exportOpts);
        doc.close(SaveOptions.DONOTSAVECHANGES);

        if (!outputFile.exists) {
            throw new Error("Export failed — output PNG was not created");
        }
    } catch (e) {
        writeError(e.message || e);
        throw e;
    }
})();
