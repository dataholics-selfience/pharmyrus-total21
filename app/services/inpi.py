"""
INPI Service - SIMPLIFIED VERSION
Only essential queries to avoid timeout
"""
import requests
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class INPIService:
    """Simplified INPI crawler"""
    
    CRAWLER_URL = "https://crawler3-production.up.railway.app/api/data/inpi/patents"
    
    def __init__(self):
        self.session = requests.Session()
    
    def search_patents(self, molecule: str, dev_codes: List[str] = None, brand: str = None) -> List[Dict]:
        """Simplified search - only 3 queries max"""
        logger.info(f"🔍 INPI: SIMPLIFIED search for {molecule}")
        
        queries = [molecule]
        
        if brand:
            queries.append(brand)
        
        if dev_codes and len(dev_codes) > 0:
            queries.append(dev_codes[0])  # Only first dev code
        
        all_patents = []
        seen = set()
        
        for query in queries[:3]:  # MAX 3 queries
            try:
                logger.info(f"   INPI query: {query}")
                params = {'medicine': query}
                resp = self.session.get(self.CRAWLER_URL, params=params, timeout=30)
                
                if resp.ok:
                    data = resp.json()
                    patents_data = data.get('data', [])
                    
                    for p in patents_data:
                        title = p.get('title', '')
                        if not title.startswith('BR'):
                            continue
                        
                        pub_num = title.replace(' ', '-')
                        if pub_num in seen:
                            continue
                        
                        seen.add(pub_num)
                        all_patents.append({
                            'publication_number': pub_num,
                            'title': p.get('applicant', ''),
                            'abstract': (p.get('fullText', '') or '')[:300],
                            'assignee': p.get('applicant', ''),
                            'filing_date': p.get('depositDate', ''),
                            'patent_type': 'INPI',
                            'link': f"https://busca.inpi.gov.br/pePI/servlet/PatenteServletController?Action=detail&CodPedido={title}",
                            'source': 'inpi_crawler',
                            'score': 8
                        })
                    
                    logger.info(f"   ✅ {query}: {len(patents_data)} results")
                
            except Exception as e:
                logger.error(f"   ❌ INPI query failed: {str(e)}")
                continue
        
        logger.info(f"✅ INPI: Total {len(all_patents)} BR patents")
        return all_patents
