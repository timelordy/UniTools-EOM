# -*- coding: utf-8 -*-

import adapters
import domain
import constants

def run(doc, output):
    output.print_md('# Поиск корзин в связях')
    
    links = adapters.get_links(doc)
    output.print_md('Найдено связей: **{}**'.format(len(links)))
    
    keywords = constants.KEYWORDS
    categories = adapters.get_categories()
    
    for ln in links:
        try:
            name = ln.Name
            link_doc = adapters.get_link_doc(ln)
            if not link_doc:
                output.print_md('- {}: **Не загружена**'.format(name))
                continue
                
            output.print_md('---')
            output.print_md('### Связь: {}'.format(name))
            
            found_count = 0
            
            for bic in categories:
                col = adapters.collect_elements(link_doc, bic)
                
                for e in col:
                    e_name, sym_name, fam_name = adapters.get_element_names(e)
                    full_text = "{} {} {}".format(e_name, sym_name, fam_name)
                    
                    matches = domain.check_keywords(full_text, keywords)
                    if matches:
                        cat_name = adapters.get_category_name(link_doc, bic)
                        output.print_md("- **Найдено**: [{}] {} / {} / {}".format(
                            cat_name, fam_name, sym_name, e_name
                        ))
                        found_count += 1
                        if found_count > 20:
                            output.print_md("... (слишком много результатов)")
                            break
                if found_count > 20: break
            
            if found_count == 0:
                output.print_md("Корзины не найдены по ключевым словам: " + ", ".join(keywords))
                
        except Exception as ex:
            output.print_md("Ошибка при обработке {}: {}".format(name, ex))