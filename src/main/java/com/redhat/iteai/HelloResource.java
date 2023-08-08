package com.redhat.iteai;

import java.io.File;
import java.io.IOException;
import java.nio.file.Paths;

import org.graalvm.polyglot.Context;
import org.graalvm.polyglot.Source;
import org.graalvm.polyglot.Value;
import org.graalvm.polyglot.io.IOAccess;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

@Path("/hello")
public class HelloResource {
    public static Context context = Context
        .newBuilder()
        .option("python.Executable", Paths.get(System.getProperty("user.dir"), "src/main/resources/venv/bin/graalpy").toString())
        .allowIO(IOAccess.ALL)
        .allowAllAccess(true)
        .build();

    void printIt(String path) {
        Object resourceStream = HelloResource.class.getResourceAsStream(path);
        System.out.println("Path: " + path + " - " + resourceStream);
    }

    @GET
    @Produces(MediaType.TEXT_PLAIN)
    public String hello() throws IOException {
        printIt("/src/main/resources/resources/languages/python/native-image.properties");
        printIt("/main/resources/resources/languages/python/native-image.properties");
        printIt("/resources/languages/python/native-image.properties");
        printIt("/languages/python/native-image.properties");
        printIt("/python/native-image.properties");
        printIt("/native-image.properties");
        printIt("/languages/python/lib/python3.10/platform.py");
        //final URL effectPy = getClass().getClassLoader().getResource("effect.py");
        File path = new File("src/main/resources/effect.py");
        System.out.println(path);
        Value effectValue = context.eval(Source.newBuilder("python", path).build());
        return "Hello from quarkus: " + effectValue + "\n";
    }
}
