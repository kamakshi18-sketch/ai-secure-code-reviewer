from typing import List, Dict, Any, Optional
import structlog
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
import asyncio
import hashlib
import json
import os
from pathlib import Path

from core.config import settings
from core.logging import get_logger

logger = get_logger("rag.engine")


class RAGEngine:
    def __init__(self):
        self.client: Optional[chromadb.Client] = None
        self.collection: Optional[chromadb.Collection] = None
        self.embedding_model: Optional[SentenceTransformer] = None
        self._initialized = False
    
    async def initialize(self):
        if self._initialized:
            return
        
        try:
            self.client = chromadb.HttpClient(
                host=settings.CHROMADB_URL.replace("http://", "").split(":")[0],
                port=int(settings.CHROMADB_URL.split(":")[-1]) if ":" in settings.CHROMADB_URL else 8000,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            
            self.collection = self.client.get_or_create_collection(
                name="security_knowledge",
                metadata={"hnsw:space": "cosine"}
            )
            
            self.embedding_model = SentenceTransformer(settings.RAG_EMBEDDING_MODEL)
            
            self._initialized = True
            logger.info("RAG engine initialized")
            
            await self._load_default_knowledge()
            
        except Exception as e:
            logger.error("Failed to initialize RAG engine", error=str(e))
            self._initialized = False
    
    async def _load_default_knowledge(self):
        count = self.collection.count()
        if count > 0:
            logger.info("Knowledge base already populated", count=count)
            return
        
        knowledge_items = self._get_default_knowledge()
        
        for item in knowledge_items:
            await self.add_document(
                source=item["source"],
                source_id=item["source_id"],
                content=item["content"],
                metadata=item["metadata"]
            )
        
        logger.info("Default knowledge loaded", items=len(knowledge_items))
    
    def _get_default_knowledge(self) -> List[Dict[str, Any]]:
        return [
            {
                "source": "owasp_top_10",
                "source_id": "a01_broken_access_control",
                "content": """OWASP A01:2021 - Broken Access Control
Access control enforces policy such that users cannot act outside of their intended permissions. Failures typically lead to unauthorized information disclosure, modification, or destruction of all data or performing a business function outside the user's limits.

Common vulnerabilities:
- Violation of the principle of least privilege
- Bypassing access control checks by modifying URL, internal application state, or HTML page
- Allowing primary key to be changed to another user's record
- Elevation of privilege
- Missing authorization checks for critical functions

Prevention:
- Implement access control mechanisms once and re-use them throughout the application
- Use server-side authorization checks for every request
- Deny by default
- Log access control failures
- Rate limit API and controller access""",
                "metadata": {"category": "access_control", "severity": "high", "owasp": "A01"}
            },
            {
                "source": "owasp_top_10",
                "source_id": "a02_cryptographic_failures",
                "content": """OWASP A02:2021 - Cryptographic Failures
Focus on failures related to cryptography which often leads to sensitive data exposure or system compromise.

Common vulnerabilities:
- Transmitting data in clear text (HTTP, SMTP, FTP)
- Using old/weak cryptographic algorithms (MD5, SHA1, DES, RC4)
- Using default/weak crypto keys
- Not using proper key rotation
- Not using authenticated encryption
- Padding oracle attacks

Prevention:
- Classify data processed, stored, or transmitted
- Encrypt all sensitive data at rest and in transit
- Use strong, up-to-date cryptographic algorithms (AES-GCM, ChaCha20-Poly1305)
- Use proper key management
- Implement certificate pinning
- Use TLS 1.2+ for all connections""",
                "metadata": {"category": "cryptography", "severity": "high", "owasp": "A02"}
            },
            {
                "source": "owasp_top_10",
                "source_id": "a03_injection",
                "content": """OWASP A03:2021 - Injection
Injection flaws occur when untrusted data is sent to an interpreter as part of a command or query. The attacker's hostile data can trick the interpreter into executing unintended commands or accessing data without proper authorization.

Types:
- SQL Injection
- NoSQL Injection
- Command Injection
- LDAP Injection
- XPath Injection
- Template Injection

Prevention:
- Use parameterized queries / prepared statements
- Use ORM frameworks with built-in protection
- Validate/sanitize input with allow-lists
- Escape special characters
- Use LIMIT and other controls
- Implement least privilege for database accounts""",
                "metadata": {"category": "injection", "severity": "critical", "owasp": "A03"}
            },
            {
                "source": "owasp_top_10",
                "source_id": "a04_insecure_design",
                "content": """OWASP A04:2021 - Insecure Design
Insecure design refers to missing or ineffective control design. It's not about implementation bugs but about fundamental design flaws.

Examples:
- Missing business logic validation
- Insufficient threat modeling
- Missing security requirements
- Insecure default configurations

Prevention:
- Establish secure design patterns
- Threat modeling during design phase
- Security requirements alongside functional requirements
- Secure design reviews
- Use established security frameworks""",
                "metadata": {"category": "design", "severity": "high", "owasp": "A04"}
            },
            {
                "source": "owasp_top_10",
                "source_id": "a05_security_misconfiguration",
                "content": """OWASP A05:2021 - Security Misconfiguration
Security misconfiguration is the most commonly seen issue. This is commonly a result of insecure default configurations, incomplete configurations, open cloud storage, misconfigured HTTP headers, and verbose error messages containing sensitive information.

Common issues:
- Unnecessary features enabled (ports, services, pages, accounts)
- Default accounts and passwords
- Error handling revealing stack traces
- Outdated software
- Missing security headers
- Improper CORS configuration

Prevention:
- Automated secure deployment processes
- Minimal platform without unnecessary features
- Regular security scanning
- Segmented application architecture
- Security headers (CSP, HSTS, X-Frame-Options, etc.)
- Automated configuration monitoring""",
                "metadata": {"category": "configuration", "severity": "medium", "owasp": "A05"}
            },
            {
                "source": "owasp_top_10",
                "source_id": "a06_vulnerable_components",
                "content": """OWASP A06:2021 - Vulnerable and Outdated Components
You are likely vulnerable if you don't know the versions of all components you use (both client-side and server-side), or if software is vulnerable, unsupported, or out of date.

Prevention:
- Inventory all components (SBOM)
- Monitor for vulnerabilities (CVE, NVD)
- Remove unused dependencies
- Use only trusted sources
- Monitor for unmaintained components
- Automate patching
- Virtual patching for legacy systems""",
                "metadata": {"category": "dependencies", "severity": "high", "owasp": "A06"}
            },
            {
                "source": "owasp_top_10",
                "source_id": "a07_auth_failures",
                "content": """OWASP A07:2021 - Identification and Authentication Failures
Confirmation of user's identity, authentication, and session management is critical to protect against authentication-related attacks.

Common vulnerabilities:
- Permitting automated attacks (credential stuffing)
- Permitting brute force
- Weak passwords
- Weak credential recovery
- Plain text/encrypted/hardcoded passwords
- Missing MFA
- Session fixation
- Exposed session IDs in URLs
- No session invalidation

Prevention:
- Implement MFA
- Prevent brute force
- Strong password policies
- Secure credential recovery
- Store passwords with strong hashing (bcrypt, scrypt, Argon2)
- Secure session management
- Rotate/invalidate sessions""",
                "metadata": {"category": "authentication", "severity": "critical", "owasp": "A07"}
            },
            {
                "source": "owasp_top_10",
                "source_id": "a08_software_integrity",
                "content": """OWASP A08:2021 - Software and Data Integrity Failures
Software and data integrity failures relate to code and infrastructure that does not protect against integrity violations.

Examples:
- Insecure CI/CD pipelines
- Unsigned software updates
- Insecure deserialization
- Auto-update without integrity verification

Prevention:
- Digital signatures for software updates
- Signed commits and verified builds
- Supply chain security (SLSA, in-toto)
- Integrity checks for serialization
- Code signing
- SBOM generation and verification""",
                "metadata": {"category": "integrity", "severity": "high", "owasp": "A08"}
            },
            {
                "source": "owasp_top_10",
                "source_id": "a09_logging_failures",
                "content": """OWASP A09:2021 - Security Logging and Monitoring Failures
Without logging and monitoring, breaches cannot be detected. Insufficient logging and monitoring allows attackers to further attack systems.

Prevention:
- Log all login, access control, and input validation failures
- Generate logs in standard format
- Ensure log integrity
- Real-time alerting
- Incident response plan
- Audit trails for sensitive operations""",
                "metadata": {"category": "logging", "severity": "medium", "owasp": "A09"}
            },
            {
                "source": "owasp_top_10",
                "source_id": "a10_ssrf",
                "content": """OWASP A10:2021 - Server-Side Request Forgery (SSRF)
SSRF flaws occur when a web application fetches a remote resource without validating the user-supplied URL. It allows an attacker to coerce the application to send a crafted request to an unexpected destination.

Prevention:
- Validate/sanitize user-supplied URLs
- Use allow-lists for allowed destinations
- Disable unused URL schemas
- Implement network segmentation
- Don't send raw responses to clients
- Use dedicated internal service mesh""",
                "metadata": {"category": "ssrf", "severity": "high", "owasp": "A10"}
            },
            {
                "source": "cwe",
                "source_id": "cwe-89",
                "content": """CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')
The product constructs all or part of an SQL command using externally-influenced input from an upstream component, but it does not neutralize or incorrectly neutralizes special elements that could modify the intended SQL command when it is sent to a downstream component.

Impact: Attackers can execute arbitrary SQL commands, leading to data theft, modification, or deletion.

Mitigation:
- Use parameterized queries (prepared statements)
- Use ORM with parameter binding
- Input validation with allow-lists
- Escape user input (last resort)
- Least privilege database accounts
- Web Application Firewall (WAF)""",
                "metadata": {"cwe_id": "CWE-89", "category": "injection"}
            },
            {
                "source": "cwe",
                "source_id": "cwe-79",
                "content": """CWE-79: Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')
The product does not neutralize or incorrectly neutralizes user-controllable input before it is placed in output that is used as a web page that is served to other users.

Types:
- Reflected XSS
- Stored XSS
- DOM-based XSS

Mitigation:
- Context-aware output encoding
- Content Security Policy (CSP)
- Input validation
- HttpOnly cookies
- Modern frameworks with auto-escaping""",
                "metadata": {"cwe_id": "CWE-79", "category": "xss"}
            },
            {
                "source": "cwe",
                "source_id": "cwe-78",
                "content": """CWE-78: Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')
The product constructs all or part of an OS command using externally-influenced input from an upstream component, but it does not neutralize or incorrectly neutralizes special elements that could modify the intended OS command when it is sent to a downstream component.

Mitigation:
- Avoid shell=True
- Use subprocess with list arguments
- Input validation with allow-lists
- Use built-in library functions instead of shell commands
- Principle of least privilege""",
                "metadata": {"cwe_id": "CWE-78", "category": "command_injection"}
            },
            {
                "source": "cwe",
                "source_id": "cwe-22",
                "content": """CWE-22: Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')
The product uses external input to construct a pathname that is intended to identify a file or directory that is located underneath a restricted parent directory, but the product does not properly neutralize special elements within the pathname that can cause the pathname to resolve to a location that is outside of the restricted directory.

Mitigation:
- Validate input against allow-list
- Use os.path.basename() or similar
- Resolve paths and verify they're within allowed directory
- Use secure file APIs
- Chroot/jail processes""",
                "metadata": {"cwe_id": "CWE-22", "category": "path_traversal"}
            },
            {
                "source": "cwe",
                "source_id": "cwe-798",
                "content": """CWE-798: Use of Hard-coded Credentials
The product contains hard-coded credentials, such as a password or cryptographic key, which it uses for its own inbound authentication, outbound communication to external components, or encryption of internal data.

Mitigation:
- Use environment variables
- Use secret management systems (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault)
- Use configuration files with restricted permissions (not in version control)
- Rotate credentials regularly
- Use short-lived tokens""",
                "metadata": {"cwe_id": "CWE-798", "category": "secrets"}
            },
            {
                "source": "cwe",
                "source_id": "cwe-502",
                "content": """CWE-502: Deserialization of Untrusted Data
The application deserializes untrusted data without sufficiently verifying that the resulting data will be valid.

Mitigation:
- Avoid deserialization of untrusted data
- Use safe deserialization libraries
- Implement integrity checks
- Use allow-lists for allowed classes
- Sign serialized data""",
                "metadata": {"cwe_id": "CWE-502", "category": "deserialization"}
            },
            {
                "source": "cert_python",
                "source_id": "sql_injection_python",
                "content": """Python Secure Coding - SQL Injection Prevention
Use parameterized queries with placeholders:

# Bad - String formatting
cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")

# Good - Parameterized query
cursor.execute("SELECT * FROM users WHERE name = %s", (name,))

# Good - Using ORM (SQLAlchemy)
session.query(User).filter(User.name == name).all()

# Good - Using psycopg2
cursor.execute("SELECT * FROM users WHERE name = %s", [name])

Always validate and sanitize input. Use allow-lists for known good values.
Limit database permissions - use least privilege accounts.""",
                "metadata": {"language": "python", "category": "injection"}
            },
            {
                "source": "cert_python",
                "source_id": "command_injection_python",
                "content": """Python Secure Coding - Command Injection Prevention
Never use shell=True with user input:

# Bad
subprocess.run(f"ping {host}", shell=True)
os.system(f"ping {host}")

# Good - Use list arguments, shell=False
subprocess.run(["ping", "-c", "4", host], capture_output=True)

# Good - Use built-in libraries
import socket
socket.gethostbyname(host)

# Good - Use shlex.quote if shell is absolutely required
import shlex
cmd = f"ping -c 4 {shlex.quote(host)}"
subprocess.run(cmd, shell=True)

Validate input against allow-list of allowed values.""",
                "metadata": {"language": "python", "category": "command_injection"}
            },
            {
                "source": "cert_python",
                "source_id": "path_traversal_python",
                "content": """Python Secure Coding - Path Traversal Prevention
Always validate and sanitize file paths:

# Bad
filepath = os.path.join(base_dir, user_filename)

# Good - Use basename
filepath = os.path.join(base_dir, os.path.basename(user_filename))

# Good - Resolve and verify
requested_path = os.path.normpath(os.path.join(base_dir, user_filename))
if not requested_path.startswith(os.path.abspath(base_dir)):
    raise ValueError("Path traversal attempt")

# Good - Use pathlib
from pathlib import Path
base = Path(base_dir).resolve()
requested = (base / user_filename).resolve()
if not requested.is_relative_to(base):
    raise ValueError("Path traversal attempt")
requested.read_text()""",
                "metadata": {"language": "python", "category": "path_traversal"}
            },
            {
                "source": "cert_python",
                "source_id": "deserialization_python",
                "content": """Python Secure Coding - Insecure Deserialization Prevention
Avoid pickle and unsafe deserialization:

# Bad
import pickle
data = pickle.loads(untrusted_data)

# Good - Use JSON
import json
data = json.loads(untrusted_data)

# Good - Use safe YAML
import yaml
data = yaml.safe_load(untrusted_data)

# Good - Use marshmallow for validation
from marshmallow import Schema, fields
class UserSchema(Schema):
    name = fields.Str()
    email = fields.Email()
data = UserSchema().load(untrusted_data)""",
                "metadata": {"language": "python", "category": "deserialization"}
            },
            {
                "source": "cert_javascript",
                "source_id": "xss_javascript",
                "content": """JavaScript/TypeScript Secure Coding - XSS Prevention

React:
// Good - Auto-escaping
<div>{userInput}</div>

// Dangerous - Only if absolutely necessary
<div dangerouslySetInnerHTML={{__html: sanitizedHtml}} />

Vue:
// Good - Auto-escaping
<div>{{ userInput }}</div>

// Dangerous
<div v-html="sanitizedHtml" />

Node.js/Express:
Use helmet.js for security headers:
app.use(helmet());

Use CSP:
app.use(helmet.contentSecurityPolicy({
  directives: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'"],
    styleSrc: ["'self'", "'unsafe-inline'"],
  }
}));

Template engines:
- Use auto-escaping templates (Nunjucks, Handlebars with escaping)
- Never use unescaped output
- Sanitize with DOMPurify for HTML content""",
                "metadata": {"language": "javascript", "category": "xss"}
            },
            {
                "source": "cert_javascript",
                "source_id": "sql_injection_javascript",
                "content": """JavaScript/TypeScript Secure Coding - SQL Injection Prevention

// Bad - String concatenation
const query = `SELECT * FROM users WHERE name = '${name}'`;
db.query(query);

// Good - Parameterized queries (pg, mysql2, etc.)
const query = 'SELECT * FROM users WHERE name = $1';
const result = await db.query(query, [name]);

// Good - Using ORM (Prisma, TypeORM, Sequelize)
const user = await prisma.user.findUnique({ where: { name } });

// Good - Using query builder (Knex)
const user = await knex('users').where('name', name).first();

Never build SQL queries by string concatenation with user input.""",
                "metadata": {"language": "javascript", "category": "injection"}
            },
            {
                "source": "cert_java",
                "source_id": "sql_injection_java",
                "content": """Java Secure Coding - SQL Injection Prevention

// Bad - String concatenation
String query = "SELECT * FROM users WHERE name = '" + name + "'";
Statement stmt = conn.createStatement();
ResultSet rs = stmt.executeQuery(query);

// Good - PreparedStatement
String query = "SELECT * FROM users WHERE name = ?";
PreparedStatement pstmt = conn.prepareStatement(query);
pstmt.setString(1, name);
ResultSet rs = pstmt.executeQuery();

// Good - Using JPA/Hibernate
@Query("SELECT u FROM User u WHERE u.name = :name")
User findByName(@Param("name") String name);

// Good - Using Spring Data JPA
interface UserRepository extends JpaRepository<User, Long> {
    User findByName(String name);
}

Always use PreparedStatement or ORM parameter binding.""",
                "metadata": {"language": "java", "category": "injection"}
            },
        ]
    
    async def add_document(
        self,
        source: str,
        source_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> str:
        if not self._initialized:
            await self.initialize()
        
        doc_id = hashlib.sha256(f"{source}:{source_id}".encode()).hexdigest()[:16]
        
        chunks = self._chunk_text(content)
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            embedding = self.embedding_model.encode(chunk).tolist()
            
            self.collection.add(
                ids=[chunk_id],
                documents=[chunk],
                embeddings=[embedding],
                metadatas=[{
                    **metadata,
                    "source": source,
                    "source_id": source_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }]
            )
        
        return doc_id
    
    def _chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
        overlap = overlap or settings.RAG_CHUNK_OVERLAP
        
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            
            if end < len(text):
                last_period = chunk.rfind('. ')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                if break_point > chunk_size // 2:
                    end = start + break_point + 1
                    chunk = text[start:end]
            
            chunks.append(chunk.strip())
            start = end - overlap
        
        return chunks
    
    async def query(
        self,
        query: str,
        top_k: int = None,
        threshold: float = None,
        filter_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        if not self._initialized:
            await self.initialize()
        
        if not self._initialized:
            return []
        
        top_k = top_k or settings.RAG_TOP_K
        threshold = threshold or settings.RAG_SIMILARITY_THRESHOLD
        
        query_embedding = self.embedding_model.encode(query).tolist()
        
        where = filter_metadata if filter_metadata else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        documents = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 1.0
                similarity = 1 - distance
                
                if similarity >= threshold:
                    documents.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "similarity": similarity,
                        "distance": distance
                    })
        
        return documents
    
    async def query_by_cwe(self, cwe_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return await self.query(
            f"CWE {cwe_id} vulnerability mitigation secure coding",
            top_k=top_k,
            filter_metadata={"cwe_id": cwe_id}
        )
    
    async def query_by_owasp(self, owasp_category: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return await self.query(
            f"OWASP {owasp_category} prevention secure coding",
            top_k=top_k,
            filter_metadata={"owasp": owasp_category}
        )
    
    async def query_by_language(self, language: str, vulnerability_type: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return await self.query(
            f"{vulnerability_type} secure coding {language} prevention",
            top_k=top_k,
            filter_metadata={"language": language}
        )
    
    async def update_source(self, source: str, url: str):
        logger.info("Updating knowledge source", source=source, url=url)
        pass


rag_engine = RAGEngine()