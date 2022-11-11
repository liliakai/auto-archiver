from typing import Union, Dict
from __future__ import annotations
from dataclasses import dataclass

"""
how not to couple the different pieces of logic
due to the use of constants for the metadata keys?
perhaps having methods on the Metadata level that can be used to fetch a limited number of
keys, never using strings but rather methods?
eg: m = Metadata() 
    m.get("screenshot") vs m.get_all()
    m.get_url()
    m.get_hash()
    m.get_main_file().get_title()
    m.get_screenshot() # this method should only exist because of the Screenshot Enricher
    # maybe there is a way for Archivers and Enrichers and Storages to add their own methdods
    # which raises still the Q of how the database, eg., knows they exist? 
    # maybe there's a function to fetch them all, and each Database can register wathever they get
    # for eg the GoogleSheets will only register based on the available column names, it knows what it wants
    # and if it's there: great, otherwise business as usual.
    # and a MongoDatabase could register all data, for example.
    # 
How are Orchestrators created? from a configuration file?
    orchestrator = ArchivingOrchestrator(config)
        # Config contains 1 URL, or URLs, from the command line
        # OR a feeder which is described in the config file
        # config.get_feeder() # if called as docker run --url "http...." then the uses the default filter
        # if config.yaml says config
    orchestrator.start()


Example applications:
1. auto-archiver for GSheets
2. archiver for URL: feeder is CLIFeeder(config.cli.urls="") # --urls="u1,u2"
3. archiver backend for a UI that implements a REST API, the API calls CLI

Cisticola considerations:
1. By isolating the archiving logic into "Archiving only pieces of logic" these could simply call cisticola.tiktok_scraper(user, pass)
2. So the auto-archiver becomes like a puzzle and fixes to Cisticola scrapers can immediately benefit it, and contributions are focused on a single source or scraping
"""

@dataclass
class Metadata:
    # does not handle files, only primitives
    # the only piece of logic to handle files is the archiver, enricher, and storage
    status: str
    # title: str
    # url: str
    # hash: str
    main_file: Metadata
    metadata: Dict[str, Metadata]

    @staticmethod
    def merge(left, right : Metadata, overwrite_left=True) -> Metadata:
        # should return a merged version of the Metadata
        # will work for archived() and enriched()
        # what if 2 metadatas contain the same keys? only one can remain! : overwrite_left
        pass

    def get(self, key) -> Union[Metadata, str]:
        # goes through metadata and returns the Metadata available
        pass

    def as_json(self) -> str:
        # converts all metadata and data into JSON
        pass


"""
@dataclass
class ArchiveResult:
    # maybe metadata can have status as well, eg: screenshot fails. should that be registered in the databases? likely yes
    status: str
    url: str
    metadata: Metadata
    # title, url, hash, other={}
    # cdn_url: str = None
    # thumbnail: str = None
    # thumbnail_index: str = None
    # duration: float = None
    # title: str = None
    # timestamp: datetime.datetime = None
    # screenshot: str = None
    # wacz: str = None
    # hash: str = None
    # media: list = field(default_factory=list)

    def __init__(self) -> None: pass

    def update(self, metadata) -> None:
        # receive a Metadata instance and update itself with it!
        pass

    def as_json(self) -> str:
        # converts all metadata and data into JSON
        pass
"""

"""
There is a Superclass for:
    * Database (should_process)

How can GSheets work? it needs to feed from a READER (GSheets Feeder)

Once an archiver returns a link to a local file (for eg to a storage), how do we then delete the produced local files? 
The context metadata should include a temporary folder (maybe a LocalStorage instance?)
"""

class ArchivingOrchestrator:
    def __init__(self, config) -> None:
        # in config.py we should test that the archivers exist and log mismatches (blocking execution)
        # identify each formatter, storage, database, etc
        self.feeder = Feeder.init(config.feeder, config.get(config.feeder))
        
        # Is it possible to overwrite config.yaml values? it could be useful: share config file and modify gsheets_feeder.sheet via CLI
        # where does that update/processing happen? in config.py
        # reflection for Archiver to know wihch child classes it has? use Archiver.__subclasses__
        self.archivers = [
            Archiver.init(a, config.get(a))
            for a in config.archivers
        ]

        self.enrichments = [
            Enrichment.init(e, config.get(e))
            for e in config.enrichments
        ]

        self.formatters = [
            Formatter.init(f, config.get(f))
            for f in config.formatters
        ]

        self.storages = [
            Storage.init(s, config.get(s))
            for s in config.storages
        ]

        self.databases = [
            Database.init(f, config.get(f))
            for f in config.formatters
        ]

        # these rules are checked in config.py
        assert len(archivers) > 1, "there needs to be at least one Archiver"

    def feed(self, feeder: Feeder) -> list(ArchiveResult):
        for next in feeder:
            self.archive(next)
            # how does this handle the parameters like folder which can be different for each archiver?
            # the storage needs to know where to archive!!
            # solution: feeders have context: extra metadata that they can read or ignore, 
            # all of it should have sensible defaults (eg: folder)
            # default feeder is a list with 1 element

    def archive(url) -> Union[ArchiveResult, None]:
        url = clear_url(url)
        result = Metadata(url=url)


        should_archive = True
        for d in databases: should_archive &= d.should_process(url)
        # should storages also be able to check?
        for s in storages: should_archive &= s.should_process(url)

        if not should_archive:
            return "skipping"

        # signal to DB that archiving has started
        for d in databases:
            # are the databases to decide whether to archive?
            # they can simply return True by default, otherwise they can avoid duplicates. should this logic be more granular, for example on the archiver level: a tweet will not need be scraped twice, whereas an instagram profile might. the archiver could not decide from the link which parts to archive, 
            # instagram profile example: it would always re-archive everything
            # maybe the database/storage could use a hash/key to decide if there's a need to re-archive
            if d.should_process(url):
                d.started(url)
            elif d.exists(url):
                return d.fetch(url)
            else:
                print("Skipping url")
                return

        # vk, telethon, ...
        for a in archivers:
            # with automatic try/catch in download + archived (+ the other ops below)
            # should the archivers come with the config already? are there configs which change at runtime? 
            # think not, so no need to pass config as parameter
            # do they need to be refreshed with every execution? 
            # this is where the Hashes come from, the place with access to all content
            # the archiver does not have access to storage
            result.update(a.download(url))
            if result.is_success(): break

        # what if an archiver returns multiple entries and one is to be part of HTMLgenerator?
        # should it call the HTMLgenerator as if it's not an enrichment?
        # eg: if it is enable: generates an HTML with all the returned media, should it include enrichments? yes
        # then how to execute it last? should there also be post-processors? are there other examples?
        # maybe as a PDF? or a Markdown file
        # side captures: screenshot, wacz, webarchive, thumbnails, HTMLgenerator
        for e in enrichments:
            result.update(e.enrich(result))

        # formatters, enrichers, and storages will sometimes look for specific properties: eg <li>Screenshot: <img src="{res.get("screenshot")}"> </li>
        for p in formatter:
            result.update(p.process(result))

        # storages
        for s in storages:
            for m in result.media:
                m.update(s.store(m))

        # signal completion to databases (DBs, Google Sheets, CSV, ...)
        # a hash registration service could be one database: forensic archiving
        for d in databases: d.done( result)

        return result