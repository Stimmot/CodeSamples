// omitted import statements

public final class ElasticWriter extends JCasAnnotator_ImplBase {

  // Logger
  private static final Logger LOG = LoggerFactory.getLogger(ElasticWriter.class);


  /* ---Connection--- */
  // Routing

  static final String HOST = "localhost";
  static final String SCHEME = "http";
  static final int PORT_ONE = 9200;
  static final int PORT_TWO = 9201;

  static final String INDEX = "urteile";

  protected static RestHighLevelClient restHighLevelClient;
  static ObjectMapper objectMapper = new ObjectMapper(); //needed?

  // Request
  protected static final RequestOptions COMMON_OPTIONS;
  static {
    RequestOptions.Builder builder = RequestOptions.DEFAULT.toBuilder();
    builder.addHeader("Authorization", "Bearer ");
    COMMON_OPTIONS = builder.build();
  }

  // Verbindung herstellen
  public static synchronized RestHighLevelClient makeConnection() {

    if (restHighLevelClient == null) {
      restHighLevelClient = new RestHighLevelClient(
          RestClient.builder(new HttpHost(HOST, PORT_ONE, SCHEME), new HttpHost(HOST, PORT_TWO, SCHEME)));
    }

    return restHighLevelClient;
  }

  // Verbindung trennen
  public static synchronized void closeConnection() throws IOException {
    restHighLevelClient.close();
    restHighLevelClient = null;
  }
  /* ---Connection Ende--- */



 // fixme: Elasticsearch Datenbank zufügen?
  public static AnalysisEngine getEngine()
      throws ResourceInitializationException {
    return AnalysisEngineFactory.createEngine(getEngineDescription());
  }

  @Override
  public void initialize(UimaContext context) throws ResourceInitializationException {
    super.initialize(context);
    ConfigurationParameterInitializer.initialize(this, getContext());
    ExternalResourceInitializer.initialize(this, getContext());

    // Test connection
    LOG.info("Testing connection to Elasticsearch DB");
    try {
      makeConnection();
      closeConnection();
    } catch(Exception e) {
      LOG.error("No connection possible");
    }
    LOG.info("Connection successful");
  }

  //todo: Verbindung zur Datenbank aufbauen -> einmal 

  public static AnalysisEngineDescription getEngineDescription()
      throws ResourceInitializationException {
    return AnalysisEngineFactory.createEngineDescription(
        ElasticWriter.class);
  }


  @Override
  public void process(JCas jCas) {

    String fileName = getFileName(jCas);

    JSONObject jsonFile = new JSONObject();
    LOG.info("Formed jCas={} to jsonFile={}", fileName, jsonFile);

    // Form cas into json
    try {
      jsonFile = formCasToJson(jCas);
    } catch (IOException | UIMAException e) {
      LOG.error(e.toString());
    }
    //System.out.println(jsonFile);

    // Upload it to DB
    uploadJson(jsonFile, jCas);
    LOG.info("Uploaded file={}", jsonFile);
  }


  private static JSONObject formCasToJson(JCas jCas) throws IOException, UIMAException {

    /* Schema
      {
    "_source": {
        "date": 1566338400000, x
        "strafmass_betrag": 10,
        "vorstrafe": true,
        "delikt": "Diebstahl", x
        "strafmass_tagessatz": 80,
        "schaden": 50,
        "gericht": "Amtsgericht Leipzig", x
        "gestaendnis": true,
        "location": "51.3226202, 12.376339753635913",
        "body": "\nAmtsgerich..." x
        }
      }
    */

    // Initialize json file with empty keys
    JSONObject jsonFile = new JSONObject();
    jsonFile.put("date", 0);
    jsonFile.put("gericht", "");
    jsonFile.put("delikt", "Diebstahl"); // only got one delikt at the moment
    jsonFile.put("strafmass_tagessatz", 0);
    jsonFile.put("strafmass_betrag", 0);
    jsonFile.put("schaden", 0);
    jsonFile.put("vorstrafe", null);
    jsonFile.put("gestaendnis", null);
    jsonFile.put("body", jCas.getSofaDataString());
    // todo: missing: freiheitsstrafe, other?

    // Check whether gestaendnis has been found
    boolean foundGest = false;

    // Iterate through named Entities, fill the corresponding json slots
    for (NamedEntity namedEnt : jCas.select(NamedEntity.class)) {

      switch (namedEnt.getEntityType()) {

        // date
        case "Datum":
          Long dateInMilliseconds = getCasDate(namedEnt);
          jsonFile.put("date", dateInMilliseconds);
          break;

        // gericht & location
        case "Ort":
          String gericht = namedEnt.getCoveredText();
          jsonFile.put("gericht", gericht);
          getLocation(gericht);
          break;

        // strafmass_tagessatz
        case "STRAFE_tgs":
          jsonFile.put("strafmass_tagessatz", namedEnt.getCoveredText());
          break;

        // strafmass_betrag
        case "STRAFE_btr":
          jsonFile.put("strafmass_betrag", namedEnt.getCoveredText());
          break;

        // schaden
        case "SCHADEN":
          jsonFile.put("schaden", namedEnt.getCoveredText());
          break;

        // vorstrafe
        case "VORSTR_ja":
          jsonFile.put("vorstrafe", true);
          break;
        case "VORSTR_nein":
          jsonFile.put("vorstrafe", false);
          break;

        // gestaendnis
        case "GEST_ja":
          jsonFile.put("gestaendnis", true);
          foundGest = true;
          break;
      }
    }

    // If there is no mention of gestaendnis, we assume there was none
    if (!foundGest) {
      jsonFile.put("gestaendnis", false);
    }

    return jsonFile;

  }

  private static Long getCasDate(NamedEntity namedEnt) {

    // Get string
    String casDate = namedEnt.getCoveredText();
    long milliseconds = 0;

    // Form it into standard form, to catch strings like 26. 03.2019, 31.012019, 2907.2019, 1508 2018
    String malformedDateString = "\\d{2}\\.\\d\\.\\d{2,4}";

    Pattern pattern = Pattern.compile(malformedDateString, Pattern.CASE_INSENSITIVE);
    Matcher matcher = pattern.matcher(casDate);

    if (matcher.matches())
      casDate = casDate.substring(0, 2) + "0" + casDate.substring(2);

    casDate = casDate.replace(".", "").replace(" ", "").replace("O", "0");

    for (int i=0; i<=5; i++) {
      if (i == 2 || i == 5)
        casDate = casDate.substring(0, i) + "." + casDate.substring(i);
    }

    // Convert date to milliseconds (set hours/minutes/seconds to 0, we don't have precise time)
    SimpleDateFormat sdf = new SimpleDateFormat("dd.MM.yyyy");

    try {
      Date newDate = sdf.parse(casDate);
      assert newDate != null;
      milliseconds = newDate.getTime();
    } catch (ParseException e) {
      LOG.error("Could not parse date. Milliseconds set to 0. \n" + e.toString());
    }

    return milliseconds;
  }

  private static String getLocation(String gericht) {
    //todo
    return null;
  }

  private static void uploadJson(JSONObject jsonFile, JCas jCas) {
    // Connect to DB
    makeConnection();

    // Create request
    IndexRequest indexRequest = new IndexRequest(INDEX).id("3333").source(jsonFile);

    // Index via response
    try {
      IndexResponse response = restHighLevelClient.index(indexRequest, COMMON_OPTIONS);
      //System.out.println(response);
    } catch (ElasticsearchException e) {
      e.getDetailedMessage();
      //System.out.println(e);
    } catch (java.io.IOException e) {
      e.getLocalizedMessage();
      //System.out.println(e);
    }


    // Close connection
    try {
      closeConnection();
    } catch (IOException e) {
      LOG.error(e.toString());
    }
  }

  // needed?
  private static String getFileName(final JCas jCas) {
    final String oldFileName = extractOldFilename(jCas);
    return FilenameUtils.removeExtension(oldFileName).concat(".cas.xmi");
  }

  private static String extractOldFilename(final JCas jCas) {
    final List<MetaData> metaDatas = jCas.select(MetaData.class).asList();
    if (!metaDatas.isEmpty()) {
      return metaDatas.get(0).getFileName();
    }
    return UUID.randomUUID().toString();
  }

}
