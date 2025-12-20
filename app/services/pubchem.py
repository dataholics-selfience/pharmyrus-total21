"""
PubChem API Service
Extract molecular data, dev codes, CAS, synonyms
"""
import requests
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PubChemService:
    """PubChem REST API integration"""
    
    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Pharmyrus/5.0 (Patent Research)'
        })
    
    def get_molecule_data(self, molecule_name: str) -> Dict:
        """Get complete molecule data from PubChem"""
        logger.info(f"🔍 PubChem: Searching {molecule_name}")
        
        result = {
            'cid': None,
            'cas': None,
            'molecular_formula': None,
            'molecular_weight': None,
            'iupac_name': None,
            'smiles': None,
            'inchi': None,
            'inchi_key': None,
            'dev_codes': [],
            'synonyms': []
        }
        
        try:
            # Get CID first
            cid = self._get_cid(molecule_name)
            if not cid:
                logger.warning(f"⚠️ PubChem: CID not found for {molecule_name}")
                return result
            
            result['cid'] = cid
            
            # Get properties
            props = self._get_properties(cid)
            if props:
                result.update(props)
            
            # Get synonyms
            synonyms = self._get_synonyms(cid)
            if synonyms:
                result['synonyms'] = synonyms[:100]  # Limit to 100
                result['dev_codes'] = self._extract_dev_codes(synonyms)
                result['cas'] = self._extract_cas(synonyms)
            
            logger.info(f"✅ PubChem: Found CID={cid}, {len(result['dev_codes'])} dev codes, CAS={result['cas']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ PubChem error: {str(e)}")
            return result
    
    def _get_cid(self, name: str) -> Optional[int]:
        """Get compound CID"""
        try:
            url = f"{self.BASE_URL}/compound/name/{name}/cids/JSON"
            resp = self.session.get(url, timeout=10)
            if resp.ok:
                data = resp.json()
                cids = data.get('IdentifierList', {}).get('CID', [])
                return cids[0] if cids else None
        except:
            return None
    
    def _get_properties(self, cid: int) -> Dict:
        """Get molecular properties"""
        try:
            url = f"{self.BASE_URL}/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,IUPACName,CanonicalSMILES,InChI,InChIKey/JSON"
            resp = self.session.get(url, timeout=10)
            if resp.ok:
                data = resp.json()
                props = data.get('PropertyTable', {}).get('Properties', [{}])[0]
                return {
                    'molecular_formula': props.get('MolecularFormula'),
                    'molecular_weight': props.get('MolecularWeight'),
                    'iupac_name': props.get('IUPACName'),
                    'smiles': props.get('CanonicalSMILES'),
                    'inchi': props.get('InChI'),
                    'inchi_key': props.get('InChIKey')
                }
        except:
            return {}
    
    def _get_synonyms(self, cid: int) -> List[str]:
        """Get all synonyms"""
        try:
            url = f"{self.BASE_URL}/compound/cid/{cid}/synonyms/JSON"
            resp = self.session.get(url, timeout=10)
            if resp.ok:
                data = resp.json()
                synonyms = data.get('InformationList', {}).get('Information', [{}])[0].get('Synonym', [])
                return [s for s in synonyms if s and len(s) > 2 and len(s) < 200]
        except:
            return []
    
    def _extract_dev_codes(self, synonyms: List[str]) -> List[str]:
        """Extract development codes (e.g., ODM-201, BAY-1841788)"""
        import re
        dev_pattern = re.compile(r'^[A-Z]{2,5}[-\s]?\d{3,7}[A-Z]?$', re.IGNORECASE)
        codes = []
        for s in synonyms:
            s = s.strip()
            if dev_pattern.match(s) and 'CID' not in s.upper():
                codes.append(s)
                if len(codes) >= 20:  # Limit
                    break
        return codes
    
    def _extract_cas(self, synonyms: List[str]) -> Optional[str]:
        """Extract CAS number"""
        import re
        cas_pattern = re.compile(r'^\d{2,7}-\d{2}-\d$')
        for s in synonyms:
            if cas_pattern.match(s):
                return s
        return None


# Standalone function for easy import
def get_molecule_data(molecule_name: str) -> Dict:
    """
    Standalone function to get molecule data from PubChem
    Args:
        molecule_name: Name of the molecule
    Returns:
        Dictionary with molecule data
    """
    service = PubChemService()
    return service.get_molecule_data(molecule_name)
